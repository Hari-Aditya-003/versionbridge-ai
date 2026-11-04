"""Serve the workspace and orchestrate the bundled, bounded repair."""
import difflib
import hashlib
import json
import os
import shutil
from pathlib import Path
import subprocess
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from uuid import uuid4

import history
from inference import propose
from projects import snapshot
from profiles import PROFILES

ROOT = Path(__file__).resolve().parent
IMAGE = "versionbridge-sandbox:1"
RUN_LOCK = threading.Lock()


def sandbox(command, emit, project=None, timeout=35):
    name = f"versionbridge-{uuid4().hex}"
    args = [
        "docker", "run", "--rm", "--pull", "never", "--log-driver", "none",
        "--name", name, "--network", "none",
        "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--memory", "384m", "--memory-swap", "384m", "--cpus", "1", "--pids-limit", "64",
        "--ulimit", "fsize=1048576:1048576",
        "--user", "65534:65534", "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=32m",
    ]
    if runtime := os.environ.get("SANDBOX_RUNTIME"):
        args.extend(["--runtime", runtime])
    if project:
        args.extend(["--mount", f"type=bind,src={project},dst=/project,readonly", "-w", "/project"])
    emit("sandbox", {"name": name, "status": "Dispatching",
                     "runtime": os.environ.get("SANDBOX_RUNTIME", "Docker default"),
                     "location": os.environ.get("SANDBOX_LOCATION", "Local Docker daemon"),
                     "limits": f"1 CPU · 384 MiB · 64 PIDs · {timeout}s"})
    captured = bytearray()
    timed_out = False
    with subprocess.Popen(args + [IMAGE] + command, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT) as process:
        def drain_output():
            for chunk in iter(lambda: process.stdout.read(4096), b""):
                remaining = 18000 - len(captured)
                if remaining:
                    captured.extend(chunk[:remaining])

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
    return exit_code, captured.decode(errors="replace")


def repair(emit, run_id, repository="", ref="", profile_id="pandas"):
    profile = PROFILES[profile_id]
    emit("project", {"profile": profile_id, "title": profile.title})
    command = ["python", "-m", "pytest", "-q", "--tb=short", "-p", "no:cacheprovider"]
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
        targets = [file for file in project.rglob("*.py")
                   if profile.original in file.read_text(errors="replace").splitlines()]
        if len(targets) != 1:
            raise RuntimeError("The selected profile needs exactly one supported migration line.")
        target = targets[0]
        source = target.read_text()
        path = target.relative_to(project).as_posix()
        test_files = sorted(file for file in project.rglob("*.py")
                            if file.name.startswith("test_") or file.name.endswith("_test.py"))
        if source.splitlines().count(profile.original) != 1 or target in test_files:
            raise RuntimeError("Expected exactly one supported call in application code.")
        test_digest = hashlib.sha256()
        for file in test_files:
            test_digest.update(file.relative_to(project).as_posix().encode() + b"\0")
            test_digest.update(hashlib.sha256(file.read_bytes()).digest())
        emit("stage", {"step": 0, "message": "Reproducing the failure in a fresh container…"})
        baseline, before = sandbox(command, emit, project)
        emit("log", {"label": "Baseline", "text": before})
        if baseline != 1 or profile.failure not in before:
            raise RuntimeError("The expected baseline failure was not reproduced. Check the execution log.")
        previous = None
        for attempt in range(1, 3):
            emit("stage", {"step": 1, "message": f"Preparing candidate patch · attempt {attempt}"})
            if len(source.encode()) > 24000:
                raise RuntimeError("The patch target is too large for the bounded model prompt.")
            proposal = propose(profile, before, source, previous)
            replacement = proposal.replacement
            emit("diagnosis", {"attempt": attempt, "text": proposal.diagnosis,
                               "provider": proposal.provider, "receipt": proposal.receipt})
            patched = "".join(replacement + line[len(profile.original):]
                              if line.rstrip("\r\n") == profile.original else line
                              for line in source.splitlines(keepends=True))
            diff = "".join(difflib.unified_diff(
                source.splitlines(True), patched.splitlines(True),
                f"a/{path}", f"b/{path}",
            ))
            target.write_text(patched)
            emit("stage", {"step": 2, "message": "Running the unchanged tests in a fresh container…"})
            status, after = sandbox(command, emit, project)
            emit("log", {"label": f"Verification {attempt}", "text": after})
            evidence = {"id": run_id, "provider": proposal.provider, "diff": diff,
                        "diagnosis": proposal.diagnosis, "inference": proposal.receipt,
                        "before": before, "after": after, "attempt": attempt,
                        "baseline_exit_code": baseline, "verification_exit_code": status,
                        "profile": profile_id, "commit": revision, "file": path,
                        "tests_sha256": test_digest.hexdigest(),
                        "patch_sha256": hashlib.sha256(diff.encode()).hexdigest()}
            if status == 0:
                emit("result", evidence)
                return
            emit("rejected", evidence)
            if not proposal.receipt:
                break
            previous = {"patch": replacement, "failure": after}
        raise RuntimeError("Candidate rejected. The unchanged verification suite did not pass.")


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


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT / "web", **kwargs)

    def list_directory(self, path):
        self.send_error(404)
        return None

    def do_GET(self):
        if self.path not in ("/api/history", "/api/config"):
            return super().do_GET()
        data = history.recent() if self.path == "/api/history" else {
            "public_import": bool(os.getenv("ENABLE_PUBLIC_IMPORT")),
            "mode": "Vultr inference" if os.getenv("VULTR_API_KEY") else "Local sample",
        }
        payload = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        action = {"/api/repair": repair, "/api/containment": containment}.get(self.path)
        if action is None:
            self.send_error(404)
            return
        if self.headers.get("Sec-Fetch-Site") not in (None, "same-origin"):
            self.send_error(403)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 <= size <= 2048:
                raise ValueError
            self.connection.settimeout(10)
            settings = json.loads(self.rfile.read(size)) if size else {}
            repository, ref = settings.get("repository", ""), settings.get("ref", "")
            profile_id = settings.get("profile", "pandas")
            if not isinstance(profile_id, str) or profile_id not in PROFILES:
                raise ValueError
            if not isinstance(repository, str) or not isinstance(ref, str) or len(repository) > 220 or len(ref) > 128:
                raise ValueError
        except (ValueError, AttributeError, OSError):
            self.send_error(400, "Invalid repair settings")
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
                    repair(emit, run_id, repository, ref, profile_id)
                else:
                    containment(emit)
            except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
                emit("error", {"message": str(exc)})
            if action is repair:
                status = "Verified" if events[-1]["event"] == "result" else "Unverified"
                history.save(run_id, repository or PROFILES[profile_id].title, status, events)
            if connected and events[-1]["event"] in ("result", "error"):
                self.wfile.write((json.dumps(events[-1]) + "\n").encode())
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            RUN_LOCK.release()


if __name__ == "__main__":
    host, port = os.getenv("HOST", "127.0.0.1"), int(os.getenv("PORT", "8787"))
    print(f"VersionBridge AI · http://{host}:{port}", flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()
