# Acceptance and model evaluation

Run `docker build -t versionbridge-sandbox:1 -f Sandbox.Dockerfile .`, then `python3 smoke.py`. The same smoke suite runs in GitHub Actions.

| Case | Baseline | Expected candidate outcome |
| --- | --- | --- |
| pandas 2 migration | Two failures after removal of DataFrame.append | Two passes after switching to concat |
| Pydantic settings | Two failures after BaseSettings moved | Two passes, including an environment override |
| Invoice arithmetic | Four wrong totals on the original formula | The model can author a bounded expression that passes all four cases |
| Regression guard | Standard DataFrame fails, legacy adapter preserves audit metadata | The standard frame works but the adapter loses audit metadata, so the verifier rejects the patch |
| Containment | Real network and filesystem attempts, a live infinite loop, and kernel memory-limit inspection | Restrictions observed and Docker confirms each container is gone |

For a real GitHub import without using the repository that contains all three fixtures, paste the public VersionBridge repository URL and pin ref `274b7ba6ec8fd8d418f686f37538517d4f87ca82` with the pandas profile. That immutable revision contains only the original pandas fixture. Public import is opt-in.

For a live provider comparison, check the model IDs available to your Vultr account, set `VULTR_API_KEY` through the service environment, and run:

```sh
python3 evaluate_models.py deepseek-v4.1-flash-1017 glm-5.3-flash > model-evidence.json
```

Each model sees the same thirteen supported profiles. The script ranks correct observed outcomes first, then total elapsed time. Provider errors, missing evidence and false acceptance of the regression count against the model. This comparison uses real inference requests and can consume credits. The fixtures check this repair workflow and do not establish general model quality.

## Private Dell run on November 4, 2026

The application called Qwen2.5 Coder 1.5B Instruct Q4_K_M on the Dell RTX 3050 Ti through Ollama over a loopback SSH tunnel. The application host ran the existing pytest suites in fresh Docker sandboxes. The earlier warm-up exceeded the original timeout, and initial invoice proposals failed. The final pass used structured outputs and candidate search over the observed integer examples.

| Live case | Observed result | Elapsed |
| --- | --- | --- |
| Invoice calculation | Four failing tests became four passing tests | 2.81 s |
| pandas at a pinned public GitHub commit | Two failing tests became two passing tests | 5.42 s |
| Pydantic settings migration | Two failing tests became two passing tests | 2.62 s |
| Audit metadata regression | Both candidates failed the unchanged suite and were rejected | 5.91 s |

Ollama reported all 29 layers offloaded to CUDA. Over 62 half-second device samples, peak total device memory use was 1,267 MiB, peak temperature was 58°C, and utilization reached 95% briefly. The model list reported zero resident models after the run. These measurements describe one test session. Vultr model and deployment results were pending at the time of this Dell session; subsequent results appear below.

## Expanded local release checks on November 5, 2026

The updated image was exercised with `python3 smoke.py` and `python3 api_smoke.py`. That intermediate suite contained twenty-one acceptance methods and nineteen HTTP checks. Earlier runs passed twenty acceptance methods and eighteen HTTP checks before the deployment permission regressions were added. The profile subtests include JavaScript, TypeScript, Go, Rust, Java, C++, SQLite, PostgreSQL, and the algorithm example. These runs use labeled sample patches and actual container execution.

The HTTP suite starts separate web and worker processes with a temporary database. It exercises authenticated access, duplicate submission handling, versioned routes, artifact checksums, containment dispatch, and rejection of a regression. The model transport test uses a test double. Live provider evaluation is recorded separately.

## Live Vultr model comparison on November 5, 2026

The controller called both Vultr models against all thirteen supported profiles and verified the candidates in fresh local Docker containers.

| Model | Expected outcomes | Reported total tokens | Total fixture time |
| --- | --- | --- | --- |
| GLM 5.3 Flash | 13 / 13 | 9,113 | 73.71 seconds |
| DeepSeek V4.1 Flash 1017 | 12 / 13 | 9,591 | 53.00 seconds |

Both models rejected the seeded regression. DeepSeek did not return an accepted structured proposal for the Java case. GLM 5.3 Flash was selected for deployment based on observed outcomes. These are bounded fixture results, with different controlled repair policies per profile. They do not measure general repository repair capability.

[Full model receipts, candidates, and test evidence](evidence/model-comparison-2026-11-05.json)

## Hosted Vultr acceptance run

The public HTTPS API at https://versionbridge.64.177.53.254.sslip.io processed all thirteen profiles using GLM 5.3 Flash on Vultr Serverless Inference. Twelve repairs were verified and the seeded regression was rejected. The separate containment job passed the filesystem, network, privilege, memory-cap, timeout, and cleanup checks.

The worker ran on a Vultr Atlanta shared-CPU VM. The HTTP user was independently denied Docker access. The provider key file was root-owned with mode 0600. The fourteen inference requests reserved $0.347013 against the hosted application's $4 allowance under its conservative pricing assumptions. Reservations are application bookkeeping and do not represent a Vultr billing invoice.

[Full hosted run events and provider receipts](evidence/vultr-live-qa-2026-11-05.json)

## Release regression checks on November 6, 2026

The final local run passed 23 acceptance methods and 20 HTTP integration checks. Added checks cover archive traversal and symbolic links, deeply nested package metadata, shared database write permissions, and containment history labeling. The public pinned GitHub repair also completed with live GLM inference, preserving the pinned source revision and passing both original tests.


## Recorded browser walkthrough on November 6

The live public browser session verified the pinned GitHub pandas repair, rejected the audit regression, and passed the containment lab. The browser downloaded both the Markdown report and the patch. The downloaded patch hash matched the run evidence. The mobile workspace was checked at a 390-pixel viewport without horizontal overflow.

[Browser run records](evidence/vultr-browser-demo-2026-11-06.json) · [Watch the recording](https://hari-aditya-003.github.io/versionbridge-ai/demo.html)

The recording shortens static pauses between captured frames. It preserves the actual execution results.

## V2 technical report implementation

The release adds 28 V2 unit and real-Docker methods to the retained 23 V1 acceptance methods. At the initial V2 checkpoint, the separate-worker HTTP suite had 24 checks; the current product release expands it to 27. New cases include five-track routing, provider catalogs/assets, stale/unsafe manifests, independent semantic regressions, runner/protocol protections and live telemetry authorization.

Both live backends verified the three new no-enum migration tasks. The cloud cascade used DeepSeek after a GLM rejection for settings; the Dell 1.5B model passed all three final cases on its first attempt. Earlier rejected trials are retained. See [V2 implementation and live evidence](V2_IMPLEMENTATION.md) for task scope and remaining evaluation gaps.

Measured statement coverage of the listed V2/shared core modules was 85.7% (582 of 679 statements); this is not whole-repository coverage. [Reproducible release-check receipt](evidence/v2-release-checks-2026-11-06.json).


## Product release checks on November 7, 2026

The current suite contains **56 Python test methods** (23 V1, 28 V2 and five streaming/export methods) and **27 HTTP integration checks**. Real-Docker streaming checks observe output before execution finishes; export checks cover bounded snapshots, chunk boundaries and legacy output. Node checks exercise event-driven workflow states and fixed-origin proxy routing. Content-version checks prevent stale browser assets.

The final live walkthrough verified a two-file migration with GLM 5.3 Flash: the original test changed from failed to passed, with all 102 independent checks passing. A separate seeded regression was rejected by the original suite. Containment passed its network, filesystem, privilege, timeout, memory-cap and cleanup checks. All eight recorded containers across those three tutorial jobs were removed. The live inspector was checked at a 390-pixel viewport without page overflow.

[Product QA receipt](evidence/product-live-qa-2026-11-07.json) · [Downloaded source/output/results bundle](evidence/walkthrough-run.txt) · [Silent walkthrough and editing record](DEMO.md)

An earlier optional fallback response failed structured validation. That take failed closed and is disclosed in the capture metadata; it is not counted as a verified repair. These tutorial runs and fixture suites do not establish universal language or repository coverage.
