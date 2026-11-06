"""Exercise the normal HTTP API against a separate worker and temporary database."""
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent


def main():
    with tempfile.TemporaryDirectory(prefix="versionbridge-api-") as folder, ExitStack() as stack:
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        token = secrets.token_urlsafe(32)
        env = {key: value for key, value in os.environ.items()
               if not key.startswith(("VULTR_", "VERSIONBRIDGE_", "REQUIRE_INFERENCE", "ENABLE_", "PUBLIC_DEMO", "EXTERNAL_WORKER"))}
        env.update(HOST="127.0.0.1", PORT=str(port), ENABLE_JOB_QUEUE="1", EXTERNAL_WORKER="1",
                   PUBLIC_DEMO="1", VERSIONBRIDGE_DB=str(Path(folder) / "runs.sqlite3"),
                   VERSIONBRIDGE_ACCESS_TOKEN=token)
        log = stack.enter_context((Path(folder) / "server.log").open("w+"))
        processes = []
        for entry in ("server.py", "worker.py"):
            process = subprocess.Popen([sys.executable, entry], cwd=ROOT, env=env, stdout=log, stderr=log)
            processes.append(process)
            stack.callback(stop, process)
        origin = f"http://127.0.0.1:{port}"

        def request(path, payload=None, authorized=True, key=None):
            headers = {"Content-Type": "application/json"}
            if authorized:
                headers["Authorization"] = "Bearer " + token
            if key:
                headers["Idempotency-Key"] = key
            data = json.dumps(payload).encode() if payload is not None else None
            req = Request(origin + path, data=data, headers=headers)
            try:
                with urlopen(req, timeout=10) as response:
                    raw = response.read()
                    content = response.headers.get("Content-Type", "")
                    return response.status, json.loads(raw) if "application/json" in content else raw
            except HTTPError as error:
                return error.code, error.read()

        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            try:
                if request("/readyz")[0] == 200:
                    break
            except OSError:
                pass
            assert all(process.poll() is None for process in processes), "A service exited"
            time.sleep(0.1)
        else:
            log.seek(0)
            raise RuntimeError(log.read())
        checks = 0

        def check(condition, message):
            nonlocal checks
            assert condition, message
            checks += 1
            print(f"PASS {message}", flush=True)

        check((Path(folder) / "runs.sqlite3").stat().st_mode & 0o060 == 0o060,
              "database permits the shared service group to read and write")
        check(request("/healthz", authorized=False)[0] == 200, "public health endpoint")
        check(request("/api/telemetry", authorized=False)[0] == 401, "resource telemetry requires workspace authentication")
        status, sensors = request("/api/v1/telemetry")
        check(status == 200 and all(k in sensors for k in ("sampled_at", "host", "gpu", "inference")),
              "versioned resource telemetry has explicit sensor provenance")
        check(sensors["inference"]["remote_gpu_metrics_available"] is False,
              "serverless GPU sensors are never fabricated")
        check(request("/api/v1/history", authorized=False)[0] == 401, "history requires authentication")
        check(request("/api/jobs", {"profile": "billing"}, authorized=False)[0] == 401,
              "job submission requires authentication")
        check(request("/api/repair", {"profile": "billing"})[0] == 409, "inline execution disabled")
        check(request("/api/jobs", {"profile": "pandas", "repository": "https://github.com/a/b"})[0] == 403,
              "public deployment rejects arbitrary imports")
        status, queued = request("/api/v1/jobs", {"profile": "typescript"}, key="api-smoke-request-1234")
        check(status == 202, "versioned API accepts repair")
        _, duplicate = request("/api/jobs", {"profile": "typescript"}, key="api-smoke-request-1234")
        check(duplicate["id"] == queued["id"], "retry returns same job")
        check(request("/api/jobs", {"profile": "sqlite"}, key="api-smoke-request-1234")[0] == 409,
              "conflicting retry is rejected")
        job = wait_job(request, queued["id"])
        check(job["state"] == "verified", "external worker verifies TypeScript repair")
        check(request(f"/api/jobs/{queued['id']}?cursor={job['cursor']}")[1]["events"] == [],
              "event cursor avoids duplicate events")
        status, evidence = request(f"/api/runs/{queued['id']}/report.json")
        check(status == 200 and evidence["events"][-1]["event"] == "result", "JSON evidence is downloadable")
        result = evidence["events"][-1]
        status, patch = request(f"/api/runs/{queued['id']}/patch")
        check(status == 200 and hashlib.sha256(patch).hexdigest() == result["patch_sha256"],
              "downloaded patch matches recorded checksum")
        status, markdown = request(f"/api/runs/{queued['id']}/report.md")
        check(status == 200 and b"Test comparison" in markdown, "Markdown evidence is downloadable")
        status, bundle = request(f"/api/runs/{queued['id']}/report.txt")
        check(status == 200 and b"FILES / Original" in bundle and b"Test outcomes" in bundle,
              "TXT bundle includes source files and test results")
        check(any(e["event"] == "sandbox_output" for e in evidence["events"]),
              "worker publishes captured container output")
        check(len([e for e in evidence["events"] if e["event"] == "files"]) >= 2,
              "original and candidate snapshots are available")
        _, probe = request("/api/jobs", {"task": "containment"})
        check(wait_job(request, probe["id"])["state"] == "contained", "external worker runs containment checks")
        check(any(row["id"] == probe["id"] and row["project"] == "Containment Lab"
                  for row in request("/api/history")[1]), "containment history has its own task label")
        _, regression = request("/api/jobs", {"profile": "regression"})
        rejected = wait_job(request, regression["id"])
        check(rejected["state"] == "unverified", "regression repair is rejected through API")
        check(request(f"/api/runs/{regression['id']}/patch")[0] == 409, "unverified patch cannot be exported as verified")
        check(request("/api/stats")[1]["verified"] == 1, "dashboard counts stored outcomes")
        check(request("/api/budget")[1]["reserved_usd"] == 0, "sample tests consume no inference credits")
        _, unsupported_v2 = request("/api/jobs", {"profile":"v2-settings", "attempts":1})
        check(wait_job(request, unsupported_v2["id"])["state"] == "inconclusive",
              "open-ended repair without live inference remains inconclusive")
        print(f"{checks} HTTP integration checks passed", flush=True)


def wait_job(request, job_id):
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        status, job = request("/api/jobs/" + job_id)
        assert status == 200
        if job["state"] not in ("queued", "running", "cancelling"):
            return job
        time.sleep(0.15)
    raise AssertionError("Job exceeded the integration deadline")


def stop(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


if __name__ == "__main__":
    main()
