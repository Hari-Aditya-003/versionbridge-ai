# VersionBridge AI

VersionBridge helps maintainers verify a narrow Python repair before applying it. The backend reproduces a failure in Docker, obtains a candidate patch, and reruns the same tests in a fresh container. The workspace shows both test outputs, the patch, and the lifecycle of each container. Download the diff to review or apply it yourself.

The project targets Blast Radius Zero at Vultr Agent Rush. The judging deployment uses a Vultr VM for the app and containers and Vultr Serverless Inference for patch proposals. The credential-free local demo uses labeled sample patches and real test execution. [LabLab event and rules](https://lablab.ai/ai-hackathons/vultr-hackathon/)

## Quick start

From the repository root, use Python 3.10 or newer and a running Docker engine.

```sh
docker build -t versionbridge-sandbox:1 -f Sandbox.Dockerfile .
python3 server.py
```

Open http://127.0.0.1:8787 and select **Run the demo** to open the workspace in a new tab. Select a repair, run it, and inspect its diff and before-and-after logs. Use the Containment Lab to observe network denial, a failed root filesystem write, the memory cap, and cleanup after an infinite loop reaches its deadline. Use **Run history** to reopen a completed repair and export its evidence.

| Try this | Expected outcome |
| --- | --- |
| pandas 2 migration | The original append call fails two tests. The concat repair passes both. |
| Pydantic 2 settings migration | The old import fails two tests. The replacement passes both, including an environment override. |
| Invoice total bug | The original expression fails four cases. The corrected total passes all four. |
| Audit metadata regression | The candidate fixes the original failure but drops audit metadata. An existing test catches the regression and the controller rejects the candidate. |

Run the acceptance suite after building the image. It covers repair, regression rejection, evidence, sandbox limits and cleanup. The same command runs in GitHub Actions. [Evaluation and fixture details](EVALUATION.md) · [GitHub Actions](https://github.com/Hari-Aditya-003/versionbridge-ai/actions/workflows/smoke.yml)

```sh
python3 smoke.py
```

## Verify an imported repository

Set `ENABLE_PUBLIC_IMPORT=1` when starting the local server. In the demo workspace, use **Load pinned GitHub example** for the public pandas fixture. The importer resolves the reference to a commit SHA before downloading the snapshot. [Pinned source fixture](https://github.com/Hari-Aditya-003/versionbridge-ai/tree/274b7ba6ec8fd8d418f686f37538517d4f87ca82)

The importer supports small public GitHub repositories with one matching line for the selected profile. The sandbox image provides pandas, NumPy, Pydantic, pydantic-settings, and pytest. Results describe the repository's own supplied tests. Use bundled fixtures for a controlled acceptance check and leave imports disabled on the shared demo until its execution host is hardened and tested. [Security model](SECURITY.md)

## Run with live inference

Set `VULTR_API_KEY` on the control plane. Set `VULTR_MODEL` to an identifier available to that account and use `REQUIRE_INFERENCE=1` for judging, so a missing key stops repair before any sample patch can be used. The default candidate is Qwen2.5 Coder 32B. Compare available candidates by verified outcomes, regression rejection, elapsed time, and reported token usage. [Model policy](MODELS.md) · [Evaluation command](EVALUATION.md)

For the public judging run, deploy the backend on a Vultr VM, repeat a live repair and containment run, and save the model receipt and the public HTTPS demo URL. The Docker fixtures and local browser demo have been exercised. Public Vultr deployment and authenticated model results still require an authorized environment. [Deployment instructions](deploy/README.md) · [Submission checklist](SUBMISSION.md) · [Recording guide](DEMO.md)

## Project map

| Area | Where to look |
| --- | --- |
| Browser workflow | [Homepage](web/index.html) and [demo workspace](web/demo.html) |
| Repair controller and sandbox lifecycle | [server.py](server.py) |
| Source import and supported repairs | [projects.py](projects.py) and [profiles.py](profiles.py) |
| Model response validation and receipts | [inference.py](inference.py) |
| SQLite history | [history.py](history.py) |
| End-to-end design and evidence | [Architecture](ARCHITECTURE.md) and [AegisPR comparison](COMPARISON.md) |

[MIT license](LICENSE)

[Private Dell inference setup](LOCAL_GPU.md) covers the lightweight Ollama profile and scoped repair trial.
