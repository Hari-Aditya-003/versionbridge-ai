# VersionBridge AI

[Live Vultr workspace](https://versionbridge.64.177.53.254.sslip.io/demo.html) · [Project showcase](https://hari-aditya-003.github.io/versionbridge-ai/) · [Recorded live demo](https://hari-aditya-003.github.io/versionbridge-ai/demo.html) · [Presentation](showcase/VersionBridge-Vultr-pitch.pptx) · [Architecture](ARCHITECTURE.md) · [Evaluation](EVALUATION.md) · [Deployment](DEPLOYMENT.md)

VersionBridge reproduces a supported code failure in Docker, proposes a scoped repair, and reruns the same tests in a fresh container. Review the patch, individual test outcomes, model receipt, and sandbox lifecycle before exporting the change.

The release includes a persistent job queue, browser refresh recovery, cancellation, an optional workspace access token, project metadata inspection, a usage dashboard, and downloadable JSON, Markdown, and patch artifacts. The HTTP service and execution worker can run under separate OS users. Only the worker needs Docker access and inference credentials.

## V2 update

The [technical blueprint implementation checklist](V2_IMPLEMENTATION.md) maps shipped behavior, live evidence and remaining boundaries. Three additional reviewed Python migrations use model-authored source edits without a replacement enum, including a two-file migration. The shared pipeline adds diagnostic routing, catalog-checked providers, bounded model fallback, trusted manifest hashes, independent behavior verification and source impact/attempt inspection.

The workspace includes a live resource panel for host RAM/CPU, available clock/temperature readings, and accessible local or trusted Dell GPU sensors. Serverless inference hardware readings are explicitly unavailable. Readings refresh every three seconds and identify their source.

## Run locally

Use Python 3.10 or newer and a running Docker engine.

```sh
docker build -t versionbridge-sandbox:1 -f Sandbox.Dockerfile .
ENABLE_JOB_QUEUE=1 python3 server.py
```

Open http://127.0.0.1:8787. **Run the demo** opens the workspace in a new tab. Choose an example, run it, then inspect its patch and before-and-after tests. Run the Containment Lab to observe network denial, filesystem protection, memory restrictions, timeout enforcement, and container cleanup.

The sandbox image includes Python libraries, Node 22, TypeScript 5.9.3, Go, Rust, Java, C++, and PostgreSQL. The initial build downloads the toolchains. Test execution has no network access.

| Profile | Verification |
| --- | --- |
| pandas 2 migration | Two existing tests verify the removed append API replacement. |
| Pydantic settings migration | Two tests cover loading settings and an environment override. |
| Invoice arithmetic | Four cases check the repaired total. |
| JavaScript discount cap | Node executes four cases against the actual module. |
| TypeScript inventory field | Strict type checking and three runtime cases verify the repair. |
| Go pagination | Four cases cover exact and partial pages. |
| Rust inclusive boundary | Four cases exercise equality and adjacent values. |
| Java role comparison | Four cases cover string content, case, and empty values. |
| C++ integer overflow | Four cases include large signed products with undefined-behavior sanitization. |
| SQLite and PostgreSQL query repairs | Separate disposable databases check empty inputs, missing matches, duplicates, and NULL amounts. PostgreSQL uses a local socket inside the container. |
| Binary search boundary | Four boundary tests and a comparison against 200 seeded inputs. |
| Regression rejection | The candidate fixes the original failure but breaks audit metadata. The verifier rejects it. |

These language examples are scoped, bundled repair profiles. General projects, dependency installation, and unrestricted multi-file repairs need additional adapters and validation.

## Test the application

```sh
python3 smoke.py
python3 api_smoke.py
python3 -m unittest test_v2 test_v2_sandbox -v
node --check web/app.js
node --check web/resources.js
```

The current release retains 23 V1 acceptance methods and adds 28 V2 unit/Docker methods, with 24 HTTP integration checks. The acceptance suite checks all repair profiles, rejection of weakened tests, sandbox teardown, model validation, queue behavior, inference allowances, and GPU telemetry policy. The HTTP suite starts a separate worker with a temporary database and checks authentication, idempotency, artifact checksums, queued containment, and regression rejection. It uses sample proposals and real sandbox execution, consuming no inference credits. GitHub Actions runs both suites.

## Inspect verification evidence

A candidate must preserve the collected test inventory and the set of skipped or expected-failure tests. Every remaining test must pass and the process must exit successfully. Exports include the original and candidate outcomes, patch and test hashes, execution logs, container teardown events, and provider receipt when available.

Results from imported repositories depend on their supplied tests. Structured reporting improves consistency checking but does not establish correctness outside the tested behavior.

## Import a pinned Python repository

For a private development instance, set `ENABLE_PUBLIC_IMPORT=1`. Use **Load pinned GitHub example** to retrieve the controlled pandas fixture at commit `274b7ba6ec8fd8d418f686f37538517d4f87ca82`. The importer resolves references before downloading a size-limited snapshot.

Supported imports require one matching source line and a compatible existing pytest suite. Optional scoped arithmetic repair also requires `ENABLE_SCOPED_REPAIR=1` and live inference. Public deployments use `PUBLIC_DEMO=1` to reject arbitrary repository imports. The deployed workspace can also allow the exact pinned pandas example, with the repository URL, commit, and profile checked in both the API and worker. [Security model](SECURITY.md)

## Run live inference within an allowance

Set worker-only `VULTR_API_KEY` and `VULTR_MODEL`, then use `REQUIRE_INFERENCE=1` to require live Vultr proposals. GLM 5.3 Flash is the selected model after achieving all 13 expected fixture outcomes in live evaluation. DeepSeek V4.1 Flash 1017 achieved 12 of 13 on the same cases. [Model policy](MODELS.md)

```sh
python3 evaluate_models.py deepseek-v4.1-flash-1017 glm-5.3-flash > model-evidence.json
```

The application reserves an allowance before each request. Defaults are $5 total and 30 inference requests per UTC day. Reservations remain charged against the allowance even if a request fails. Conservative input/output token prices are configurable and must cover the selected model's current rates. VM, backup, bandwidth, and other Vultr account charges are separate. [Budget configuration](.env.example)

## Separate the web service and worker

Start both processes against the same private database directory.

```sh
ENABLE_JOB_QUEUE=1 EXTERNAL_WORKER=1 python3 server.py
python3 worker.py
```

The deployment installer creates separate web and worker users. The web user has no Docker group membership or inference key. The worker holds the execution privileges and publishes results through SQLite. Use one worker per database. The worker process lock prevents duplicate worker startup.

Queued jobs survive a restart. Running jobs become interrupted after their recorded containers are cleaned up. Cancellation stops an active job at the next step boundary. The queue holds at most five active jobs and retains 100 completed jobs. Public mode permits up to 100 new jobs per UTC day. Idempotency keys prevent duplicate submissions.

## Private Dell inference

The optional Ollama mode uses a small quantized model through a loopback SSH tunnel. GPU quiet mode can require fresh telemetry, pause above 65°C, pause when utilization reaches 30%, and require 1,536 MiB of free GPU memory before dispatch. These are admission checks. Runtime power and cooling are managed by the device. [Setup and observed Dell results](LOCAL_GPU.md)

## Release scope and next work

The implemented release covers the listed scoped repair examples, Python snapshot imports, persistent jobs, bounded execution, test comparison, artifacts, model receipts, and a containment lab.

Broader repository adapters, arbitrary package installation, GitHub App authentication, automated repair PRs, organizations and roles, scheduled monitoring, arbitrary multi-file repository patches, and general independent generated regression tests remain future work. Bounded two-file Python migration and independent reviewed behavior checks are implemented in V2. Each requires its own release tests before being offered as a supported capability.

| Area | Files |
| --- | --- |
| Browser and showcase | `web/`, `showcase/` |
| Public API and controller | `server.py` |
| Separate execution worker | `worker.py` |
| Persistent queue and history | `jobs.py`, `history.py` |
| Inference policy and allowance | `inference.py`, `budget.py` |
| Verification and reports | `pytest_runner.py`, `verification.py`, `reports.py` |
| Source retrieval and inspection | `projects.py`, `inspection.py`, `profiles.py` |
| Private GPU tools | `local_gpu.py`, `gpu_guard.py`, `gpu_monitor.py` |
| Reproducible examples | `fixture/`, `scenarios/` |
| Deployment and QA | `deploy/`, `smoke.py`, `api_smoke.py` |

[MIT license](LICENSE) · [Hackathon submission checklist](SUBMISSION.md) · [AegisPR comparison](COMPARISON.md)
