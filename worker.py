"""Run the execution worker separately from the unprivileged HTTP service."""
import fcntl
import os
from pathlib import Path
import subprocess
import threading

import history
import jobs
from inference import inference_mode
from server import IMAGE, job_worker, recover_jobs


def monitor_runtime():
    while True:
        try:
            result = subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True, timeout=4)
            jobs.heartbeat(result.returncode == 0)
        except (OSError, subprocess.SubprocessError):
            jobs.heartbeat(False)
        threading.Event().wait(5)


if __name__ == "__main__":
    os.umask(0o007)
    inference_mode()
    history.DB.parent.mkdir(parents=True, exist_ok=True)
    with Path(str(history.DB) + ".worker.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        recover_jobs()
        threading.Thread(target=monitor_runtime, daemon=True).start()
        job_worker()
