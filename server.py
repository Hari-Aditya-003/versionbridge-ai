"""Serve the workspace and orchestrate the bundled, bounded repair."""
import difflib
import hmac
import logging
import hashlib
import json
import os
import re
import shutil
from pathlib import Path
import subprocess
import tempfile
import threading
from contextlib import closing
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import budget
from inspection import inspect_project
import history
import jobs
import reports
from inference import inference_mode, propose
from projects import snapshot
from profiles import PROFILES
from python_target import resolve_target
from verification import PYTEST_COMMAND, REPORT_PREFIX, REPORT_WINDOW, parse_report, verification_failure

ROOT = Path(__file__).resolve().parent
IMAGE = "versionbridge-sandbox:1"
RUN_LOCK = threading.Lock()
JOB_WAKE = threading.Event()
JOB_ROUTE = re.compile(r"/api/jobs/([a-f0-9]{32})")
QUEUE_ENABLED = False
WORKER_THREAD = None


def sandbox(command, emit, project=None, timeout=35, *, test_report=None, native=False):
    name = f"versionbridge-{uuid4().hex}"
    args = [
        "docker", "run", "--rm", "--pull", "never", "--log-driver", "none",
        "--name", name, "--network", "none",
        "--read-only", "--env", "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--memory", "384m", "--memory-swap", "384m", "--cpus", "1", "--pids-limit", "64",
        "--ulimit", "fsize=67108864:67108864",
        "--user", "65534:65534", "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=128m",
    ]
    if native:
        args.extend(["--tmpfs", "/build:rw,exec,nosuid,nodev,size=128m,mode=1777"])
    if runtime := os.environ.get("SANDBOX_RUNTIME"):
        args.extend(["--runtime", runtime])
    if project:
        args.extend(["--mount", f"type=bind,src={project},dst=/project,readonly", "-w", "/project"])
    emit("sandbox", {"name": name, "status": "Dispatching",
                     "runtime": os.environ.get("SANDBOX_RUNTIME", "Docker default"),
                     "location": os.environ.get("SANDBOX_LOCATION", "Local Docker daemon"),
                     "limits": f"1 CPU · 384 MiB · 64 PIDs · {timeout}s"})
    captured = bytearray()
    tail = bytearray()
    timed_out = False
    with subprocess.Popen(args + [IMAGE] + command, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT) as process:
        def drain_output():
            for chunk in iter(lambda: process.stdout.read(4096), b""):
                remaining = 18000 - len(captured)
                if remaining:
                    captured.extend(chunk[:remaining])
                if test_report is not None:
                    tail.extend(chunk)
                    if len(tail) > REPORT_WINDOW:
                        del tail[:-REPORT_WINDOW]

        reader = threading.Thread(target=drain_output, daemon=True)
        reader.start()
        try:
            exit_code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            process.wait()
            subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=10)
            exit_code = 124
        finally:
            reader.join(timeout=5)
    listing = subprocess.run(["docker", "ps", "-aq", "--filter", f"name=^/{name}$"],
                             capture_output=True, timeout=10, check=True)
    if listing.stdout.strip():
        raise RuntimeError("Docker still reports a sandbox after teardown.")
    emit("sandbox", {"name": name, "status": "Removed" if timed_out or exit_code < 125 else "Absent",
                     "exit_code": exit_code, "timed_out": timed_out})
    output = captured.decode(errors="replace")
    if test_report is not None:
        test_report.update(parse_report(tail))
        output = output.split("\n" + REPORT_PREFIX, 1)[0]
    return exit_code, output


def patch_diff(original, patched, path):
    def physical_lines(source):
        lines = source.split("\n")
        return [line + "\n" for line in lines[:-1]] + ([lines[-1]] if lines[-1] else [])

    lines = difflib.unified_diff(physical_lines(original), physical_lines(patched),
                                 f"a/{path}", f"b/{path}")
    return "".join(line if line.endswith("\n") else line + "\n\\ No newline at end of file\n"
                   for line in lines)


def repair(emit, run_id, repository="", ref="", profile_id="pandas", filename="", function=""):
    scoped = profile_id == "python"
    if scoped and (not os.getenv("ENABLE_SCOPED_REPAIR") or not repository):
        raise RuntimeError("Scoped Python repair requires an enabled public repository import.")
    if scoped and inference_mode() == "sample":
        raise RuntimeError("Scoped Python repair requires configured model inference.")
    profile = PROFILES.get(profile_id)
    if repository and profile and profile.bundled_only:
        raise RuntimeError("This beta profile runs its bundled project only.")
    emit("project", {"profile": profile_id, "title": "Python · scoped function repair" if scoped else profile.title})
    with tempfile.TemporaryDirectory(prefix="versionbridge-") as folder:
        project = Path(folder)
        project.chmod(0o755)
        revision = None
        if repository:
            if not os.getenv("ENABLE_PUBLIC_IMPORT"):
                raise RuntimeError("Public imports are disabled by this deployment. Try the bundled project.")
            emit("stage", {"step": 0, "message": "Resolving the public GitHub commit…"})
            revision = snapshot(repository, ref, project)
            emit("log", {"label": "Immutable GitHub snapshot", "text": revision})
        else:
            shutil.copytree(ROOT / profile.fixture, project, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        if scoped:
            target, source, profile, line_number = resolve_target(project, filename, function)
        else:
            targets = [file for file in project.rglob(f"*{profile.suffix}")
                       if profile.original in file.read_text(errors="replace").split("\n")]
            if len(targets) != 1:
                raise RuntimeError("The selected profile needs exactly one supported migration line.")
            target = targets[0]
            try:
                source = target.read_bytes().decode("utf-8")
            except UnicodeError as exc:
                raise RuntimeError("The selected source file must be valid UTF-8 Python.") from exc
            matching_lines = [index for index, line in enumerate(source.split("\n"), start=1)
                              if line.removesuffix("\r") == profile.original]
            if len(matching_lines) != 1:
                raise RuntimeError("Expected exactly one supported call in application code.")
            line_number = matching_lines[0]
        # The worker keeps its database group-private. Sanitized sandbox inputs
        # need explicit read permissions for the container's unprivileged UID.
        for item in project.rglob("*"):
            item.chmod(0o755 if item.is_dir() else 0o644)
        inventory = inspect_project(project)
        emit("inventory", inventory)
        path = target.relative_to(project).as_posix()
        test_files = sorted(file for file in project.rglob("*.py")
                            if file.name.startswith("test_") or file.name.endswith("_test.py"))
        if not test_files or target in test_files:
            raise RuntimeError("An existing pytest suite and an application source target are required.")
        test_digest = hashlib.sha256()
        for file in test_files:
            test_digest.update(file.relative_to(project).as_posix().encode() + b"\0")
            test_digest.update(hashlib.sha256(file.read_bytes()).digest())
        emit("stage", {"step": 0, "message": "Reproducing the failure in a fresh container…"})
        baseline_tests = {}
        baseline, before = sandbox(PYTEST_COMMAND, emit, project, test_report=baseline_tests, native=profile.native, timeout=profile.timeout)
        emit("log", {"label": "Baseline", "text": before})
        if baseline != 1 or (not scoped and profile.failure not in before):
            raise RuntimeError("The expected baseline failure was not reproduced. Check the execution log.")
        if "failed" not in baseline_tests.values():
            raise RuntimeError("The baseline did not report a completed failing test inventory.")
        previous = None
        for attempt in range(1, 3):
            emit("stage", {"step": 1, "message": f"Preparing candidate patch · attempt {attempt}"})
            if len(source.encode()) > 24000:
                raise RuntimeError("The patch target is too large for the bounded model prompt.")
            context = source
            if inference_mode() == "local-gpu":
                lines = source.split("\n")
                context = "\n".join(lines[max(0, line_number - 12):line_number + 4])
            proposal = propose(profile, before, context, previous)
            replacement = proposal.replacement
            emit("diagnosis", {"attempt": attempt, "text": proposal.diagnosis,
                               "provider": proposal.provider, "receipt": proposal.receipt})
            if previous and replacement == previous["patch"]:
                raise RuntimeError("Candidate rejected. The model repeated a patch that already failed verification.")
            lines = source.split("\n")
            original_line = lines[line_number - 1]
            if original_line.removesuffix("\r") != profile.original:
                raise RuntimeError("The selected source line could not be located.")
            lines[line_number - 1] = replacement + ("\r" if original_line.endswith("\r") else "")
            patched = "\n".join(lines)
            if patched == source:
                raise RuntimeError("The candidate did not change the selected statement.")
            diff = patch_diff(source, patched, path)
            target.write_bytes(patched.encode("utf-8"))
            emit("stage", {"step": 2, "message": "Running the unchanged tests in a fresh container…"})
            candidate_tests = {}
            status, after = sandbox(PYTEST_COMMAND, emit, project, test_report=candidate_tests, native=profile.native, timeout=profile.timeout)
            reason = verification_failure(baseline_tests, candidate_tests)
            if status != 0 and reason is None:
                reason = "The verification process exited unsuccessfully."
            emit("log", {"label": f"Verification {attempt}", "text": after})
            evidence = {"id": run_id, "provider": proposal.provider, "diff": diff,
                        "diagnosis": proposal.diagnosis, "inference": proposal.receipt,
                        "before": before, "after": after, "attempt": attempt,
                        "baseline_exit_code": baseline, "verification_exit_code": status,
                        "inventory": inventory,
                        "profile": profile_id, "commit": revision, "file": path,
                        "baseline_tests": baseline_tests, "verification_tests": candidate_tests,
                        "rejection_reason": reason,
                        "tests_sha256": test_digest.hexdigest(),
                        "patch_sha256": hashlib.sha256(diff.encode()).hexdigest()}
            if reason is None:
                emit("result", evidence)
                return
            emit("rejected", evidence)
            if not proposal.receipt:
                break
            previous = {"patch": replacement, "failure": after}
        raise RuntimeError("Candidate rejected. The verification gate did not pass.")


def containment(emit):
    emit("stage", {"step": 0, "message": "Probing the container’s network and filesystem…"})
    probe = """
import os, socket
from pathlib import Path
for address in ('192.0.2.1', '2001:db8::1'):
    try:
        socket.create_connection((address, 443), timeout=2).close()
    except OSError as error:
        print(f'Outbound connection to {address} blocked: {error}')
    else:
        raise AssertionError(f'Unexpected outbound connection to {address}')
assert os.statvfs('/').f_flag & os.ST_RDONLY, 'Root mount is writable'
try:
    Path('/probe').write_text('probe')
except OSError as error:
    print('Root filesystem write blocked:', error)
else:
    raise AssertionError('Unexpected root write access')
assert os.getuid() != 0
assert 'VULTR_API_KEY' not in os.environ
print('Non-root user confirmed. Inference key absent.')
"""
    status, output = sandbox(["python", "-c", probe], emit)
    emit("log", {"label": "Containment probe", "text": output})
    if status:
        raise RuntimeError("Containment probe failed. Check the execution log.")
    emit("stage", {"step": 1, "message": "Running an infinite loop against a 3-second deadline…"})
    status, _ = sandbox(["python", "-c", "while True: pass"], emit, timeout=3)
    if status != 124:
        raise RuntimeError("The timeout probe did not hit its deadline.")
    emit("log", {"label": "Timeout probe", "text": "The infinite loop hit its deadline. Docker confirms the container is gone."})
    memory_probe = """
from pathlib import Path
for path in ('/sys/fs/cgroup/memory.max', '/sys/fs/cgroup/memory/memory.limit_in_bytes'):
    if Path(path).is_file():
        limit = Path(path).read_text().strip()
        assert limit == '402653184', f'Unexpected cgroup memory limit: {limit}'
        print(f'Kernel cgroup memory cap: {limit} bytes (384 MiB).')
        break
else:
    raise RuntimeError('Memory limit is not visible inside this runtime.')
"""
    status, output = sandbox(["python", "-c", memory_probe], emit)
    emit("log", {"label": "Memory policy", "text": output})
    if status:
        raise RuntimeError("The sandbox memory cap could not be verified.")
    emit("contained", {"message": "Containment checks passed"})


def recover_jobs():
    names = {event["name"] for event in jobs.interrupted_events()
             if event["event"] == "sandbox" and re.fullmatch(r"versionbridge-[a-f0-9]{32}", event["name"])}
    if names:
        result = subprocess.run(["docker", "ps", "-a", "--format", "{{.Names}}"],
                                capture_output=True, text=True, check=True, timeout=10)
        for name in names.intersection(result.stdout.splitlines()):
            subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=10, check=True)
    jobs.interrupted()


def job_worker():
    while True:
        with RUN_LOCK:
            job = jobs.claim()
            if job:
                job_id, settings = job
                events = []

                def emit(event, data):
                    events.append({"event": event, **data})
                    if event not in ("result", "error"):
                        jobs.publish(job_id, events)

                try:
                    if len(settings) == 6 and settings[5] == "containment":
                        containment(emit)
                    else:
                        repair(emit, job_id, *settings)
                except jobs.Cancelled:
                    pass
                except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
                    emit("error", {"message": str(exc)})
                except Exception:
                    logging.exception("Repair job failed")
                    emit("error", {"message": "The repair could not complete. Review the server log for this run."})
                profile = PROFILES.get(settings[2])
                project = settings[0] or (profile.title if profile else "Python scoped repair")
                jobs.publish(job_id, events, project=project)
        if not job:
            JOB_WAKE.wait(0.5)
            JOB_WAKE.clear()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT / "web", **kwargs)

    def list_directory(self, path):
        self.send_error(404)
        return None

    def respond_json(self, status, data):
        payload = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def authorized(self):
        token = os.getenv("VERSIONBRIDGE_ACCESS_TOKEN")
        if not token or hmac.compare_digest(self.headers.get("Authorization", ""), "Bearer " + token):
            return True
        self.respond_json(401, {"message": "This workspace requires an access token."})
        return False

    def normalize_api(self):
        if self.path.startswith("/api/v1/"):
            self.path = "/api/" + self.path[len("/api/v1/"):]

    def do_GET(self):
        self.normalize_api()
        if self.path in ("/healthz", "/readyz"):
            healthy = True
            if self.path == "/readyz" and os.getenv("EXTERNAL_WORKER") == "1":
                healthy = jobs.worker_ready()
            elif self.path == "/readyz":
                try:
                    with closing(history.connect()) as db:
                        db.execute("SELECT 1").fetchone()
                    runtime = subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True, timeout=3)
                    healthy = runtime.returncode == 0 and (not QUEUE_ENABLED or WORKER_THREAD.is_alive())
                except (OSError, subprocess.SubprocessError):
                    healthy = False
            self.respond_json(200 if healthy else 503, {"status": "ok" if healthy else "worker unavailable",
                                                       "version": "0.2.0"})
            return
        if self.path.startswith("/api/") and self.path != "/api/config" and not self.authorized():
            return
        if self.path == "/api/stats":
            self.respond_json(200, history.stats())
            return
        if self.path == "/api/budget":
            self.respond_json(200, budget.status())
            return
        url = urlsplit(self.path)
        artifact = re.fullmatch(r"/api/runs/([a-f0-9]{12}|[a-f0-9]{32})/(report.json|report.md|patch)", url.path)
        if artifact:
            events = history.find(artifact[1])
            if events is None:
                self.send_error(404, "Run not found")
                return
            kind = artifact[2]
            if kind == "report.json":
                self.respond_json(200, {"events": events})
                return
            if kind == "patch":
                if events[-1]["event"] != "result":
                    self.send_error(409, "This run has no verified patch")
                    return
                content = events[-1]["diff"]
            else:
                content = reports.markdown(events)
            encoded = content.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="versionbridge-{artifact[1]}.{kind}"')
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(encoded)
            return
        if QUEUE_ENABLED and (match := JOB_ROUTE.fullmatch(url.path)):
            cursor = parse_qs(url.query).get("cursor", ["0"])[0]
            if not re.fullmatch(r"[0-9]{1,6}", cursor):
                self.send_error(400, "Invalid event cursor")
                return
            data = jobs.get(match[1], int(cursor))
            self.respond_json(200 if data else 404, data)
            return
        if self.path not in ("/api/history", "/api/config"):
            return super().do_GET()
        data = history.recent() if self.path == "/api/history" else {
            "public_import": bool(os.getenv("ENABLE_PUBLIC_IMPORT")),
            "scoped_repair": bool(os.getenv("ENABLE_SCOPED_REPAIR") and os.getenv("ENABLE_PUBLIC_IMPORT")
                                  and inference_mode() != "sample"),
            "job_queue": QUEUE_ENABLED,
            "external_worker": os.getenv("EXTERNAL_WORKER") == "1",
            "auth_required": bool(os.getenv("VERSIONBRIDGE_ACCESS_TOKEN")),
            "profiles": [{"id": key, "title": value.title, "language": value.language,
                          "bundled_only": value.bundled_only} for key, value in PROFILES.items()],
            "mode": {"vultr": "Vultr inference", "local-gpu": "Local Ollama", "sample": "Local sample"}[inference_mode()],
        }
        self.respond_json(200, data)

    def do_POST(self):
        self.normalize_api()
        if not self.authorized():
            return
        action = {"/api/repair": repair, "/api/containment": containment}.get(self.path)
        submit = QUEUE_ENABLED and self.path == "/api/jobs"
        cancel = JOB_ROUTE.fullmatch(self.path) if QUEUE_ENABLED else None
        if action is None and not submit and not cancel:
            self.send_error(404)
            return
        if self.headers.get("Sec-Fetch-Site") not in (None, "same-origin"):
            self.send_error(403)
            return
        if cancel:
            accepted = jobs.cancel(cancel[1])
            self.respond_json(202 if accepted else 409, {"accepted": accepted})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 <= size <= 2048:
                raise ValueError
            self.connection.settimeout(10)
            settings = json.loads(self.rfile.read(size)) if size else {}
            repository, ref = settings.get("repository", ""), settings.get("ref", "")
            profile_id = settings.get("profile", "pandas")
            filename, function = settings.get("filename", ""), settings.get("function", "")
            task = settings.get("task", "repair")
            if task not in ("repair", "containment"):
                raise ValueError
            if not isinstance(filename, str) or not isinstance(function, str) or len(filename) > 180 or len(function) > 80:
                raise ValueError
            if not isinstance(profile_id, str) or (profile_id not in PROFILES and profile_id != "python"):
                raise ValueError
            if not isinstance(repository, str) or not isinstance(ref, str) or len(repository) > 220 or len(ref) > 128:
                raise ValueError
        except (ValueError, AttributeError, OSError, RecursionError):
            self.send_error(400, "Invalid repair settings")
            return
        if os.getenv("PUBLIC_DEMO") == "1" and repository:
            self.respond_json(403, {"message": "The public demo runs curated projects. Use a private workspace for imports."})
            return
        if submit:
            key = self.headers.get("Idempotency-Key")
            if key and not re.fullmatch(r"[A-Za-z0-9-]{16,80}", key):
                self.send_error(400, "Invalid idempotency key")
                return
            try:
                job_settings = [repository, ref, profile_id, filename, function]
                if task == "containment":
                    job_settings.append(task)
                job_id = jobs.submit(job_settings, key)
            except ValueError as exc:
                self.respond_json(409, {"message": str(exc)})
                return
            if job_id:
                JOB_WAKE.set()
            self.respond_json(202 if job_id else 429, {"id": job_id})
            return
        if QUEUE_ENABLED or os.getenv("PUBLIC_DEMO") == "1":
            self.respond_json(409, {"message": "Use the queued job endpoint for this deployment."})
            return
        if not RUN_LOCK.acquire(blocking=False):
            self.send_error(429, "A sandbox task is already running")
            return
        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Accel-Buffering", "no")
            self.end_headers()

            run_id = uuid4().hex[:12]
            events = []
            connected = True

            def emit(event, data):
                nonlocal connected
                record = {"event": event, **data}
                events.append(record)
                if connected and event not in ("result", "error"):
                    try:
                        self.wfile.write((json.dumps(record) + "\n").encode())
                        self.wfile.flush()
                    except OSError:
                        connected = False

            try:
                if action is repair:
                    repair(emit, run_id, repository, ref, profile_id, filename, function)
                else:
                    containment(emit)
            except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
                emit("error", {"message": str(exc)})
            if action is repair:
                status = "Verified" if events[-1]["event"] == "result" else "Unverified"
                history.save(run_id, repository or (PROFILES[profile_id].title if profile_id in PROFILES else "Python scoped repair"), status, events)
            if connected and events[-1]["event"] in ("result", "error"):
                self.wfile.write((json.dumps(events[-1]) + "\n").encode())
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            RUN_LOCK.release()


if __name__ == "__main__":
    inference_mode()
    host, port = os.getenv("HOST", "127.0.0.1"), int(os.getenv("PORT", "8787"))
    print(f"VersionBridge AI · http://{host}:{port}", flush=True)
    with ThreadingHTTPServer((host, port), Handler) as server:
        QUEUE_ENABLED = os.getenv("ENABLE_JOB_QUEUE") == "1"
        if QUEUE_ENABLED and os.getenv("EXTERNAL_WORKER") != "1":
            recover_jobs()
            WORKER_THREAD = threading.Thread(target=job_worker, daemon=True)
            WORKER_THREAD.start()
        server.serve_forever()
