# V2 implementation and acceptance status

This release implements the core engineering loop from the supplied technical blueprint dated November 6, 2026. Source document SHA-256: `b25553e3fd6e4ac80850127817be6a49d8744ada4c66cf9b0a2ca094385d3725`.

The new migrations use model-authored edit spans and text, with no permitted-replacement enum or sample patch. They remain three constructed, reviewed Python projects with pinned runtime dependencies. Their success does not establish accuracy on unrelated repositories.

## Requirement mapping

| Blueprint area | Implemented and exercised | Remaining boundary |
| --- | --- | --- |
| M0 baseline | Original 23 Docker acceptance methods retained; authenticated HTTP checks expanded. Runtime image, source/test hashes and cleanup recorded. | Repository-provided tests are not an independent correctness oracle. |
| M1 provider/router | Five diagnostic tracks, multi-label/unknown, typed Vultr/Ollama contracts, registry, live Vultr catalog checks, local installed-Q4 manifest checks, requested/served attribution and sequential fallback. | No category-specific promotion without a larger held-out comparison. Draft PR #1's limited retry concept is superseded by the main implementation; the draft itself was not merged. |
| M2 genuine repair | Three no-enum migration tasks: Pydantic settings, collections ABC, and two-file imports. Model generates source spans; trusted engine binds immutable checksums. | Open-ended describes proposed edits within the reviewed application allowlist, not arbitrary repository access. |
| M3 language adapters | Explicit command/deadline/build-space contracts for nine existing environments; existing compiler/DB positive cases remain exercised. | General Node/TS/SQL/Go/Rust/Java/C++ dependency preparation and repository adapters remain unimplemented. Unsupported languages are rejected. |
| M4 multi-file | Up to four application files, eight edits, 128 affected lines, 16 KB replacement text. Two-file migration passes independent checks. Pristine source per attempt; no test or policy edits. | Arbitrary multi-file application to unreviewed public repositories is disabled. |
| M5 independent checks | Read-only supervisor runs source in a child and compares behavior outside that child. Four settings checks, 101 mapping checks, 102 cross-file checks; seed 7319. Semantic shortcut and forged-verdict negatives tested. | No general generated-test/mutation-testing engine; constructed checks cannot establish full semantic correctness or security. |
| M6 evidence/UX | Source-grounded AST symbols/import/call edges with exact/heuristic labels; category, model attempt history, diff, independent results, atomic SQLite candidate records, Markdown/JSON export. Live resource panel. | Static Python impact edges cover allowed files, not whole-program resolved graphs. Model critics are advisory infrastructure, disabled by default. |
| M7 broader deployment | Existing HTTPS deployment, separate web/worker users, optional single-workspace bearer token, daily submission/inference caps retained. | Organization roles, per-user ownership, private GitHub App access, automatic PR approval and stronger arbitrary-code isolation remain future work. |

## Trust boundary

Models supply `diagnosis` and edits containing `path`, inclusive physical `start_line`/`end_line`, `new_text`, and `reason`. They do not compute trusted checksums or decide eligibility. The worker confirms the original intake digest, calculates old-span hashes, inherits the original indentation/newline for single-line statements, and produces a versioned edit manifest. Both raw rejected proposals and final bound manifests are retained where available.

The patch engine rejects traversal, symlinks, protected paths, stale source, overlapping/oversized edits, invalid syntax, changed signatures/assertions, new module-level execution/state, runtime introspection and sensitive operations. These checks are conservative restrictions; they are not a complete Python security proof.

Original tests run in a fresh container, against the same image and test inventory. Independent checks use a read-only supervisor with process introspection disabled. Application imports occur only in a child with captured output. The supervisor checks behavior data, not a candidate-supplied pass flag. Suite identity, check count, supervisor hash, exit status and protocol must match before acceptance. Docker cleanup must complete.

An execution/policy failure is rejected. Missing backend/model evidence remains inconclusive. Human application approval remains pending even after a run is verified against its listed checks.

## Live acceptance evidence

- [Final Vultr V2 runs](evidence/vultr-v2-live-2026-11-06.json): all three tasks verified. Pydantic needed the DeepSeek fallback after a GLM policy rejection; collections and the two-file task used GLM.
- [Final Dell V2 runs](evidence/dell-v2-final-2026-11-06.json): all three tasks verified on the first attempt with Qwen2.5-Coder 1.5B Q4_K_M, 2048 context and an explicitly evaluated 800-output-token setting. Model-request times were about 3.33, 3.76 and 4.54 seconds; full pipeline time is recorded separately.
- [Initial cloud validation](evidence/vultr-v2-initial-validation-2026-11-06.json) and [checksum-stage validation](evidence/vultr-v2-checksum-validation-2026-11-06.json) retain rejected candidates that led to the trusted formatting/binding fixes. They are not counted as successful final outcomes.
- [Earlier Dell trials](evidence/dell-v2-live-2026-11-06.json), [tuning trial](evidence/dell-v2-tuned-2026-11-06.json) and [binding trial](evidence/dell-v2-bound-2026-11-06.json) retain schema, policy and quiet-mode failures. No larger model was promoted.

V1 and V2 evidence must be reported separately. The old 13-profile benchmark uses constrained replacement policies. The three new cases are controlled API migrations without an answer enum, not a representative unseen-repository benchmark.

## Resource panel

`GET /api/telemetry` (also `/api/v1/telemetry`) follows workspace authentication. The workspace polls every three seconds and pauses polling when hidden. Host CPU uses sampled counters on Linux and process estimates on macOS. RAM, available CPU frequency, accessible temperature sensors, NVIDIA utilization/VRAM and fresh trusted Dell telemetry are shown with provenance. Stale/offline values are cleared.

RAM and CPU refer to the application host. A Dell GPU monitor can supply the separate inference GPU readings. Vultr Serverless Inference GPU utilization, VRAM and temperature are not exposed by its inference API and are shown unavailable. The shared-CPU VM has no NVIDIA sensor; unavailable temperature readings are not synthesized. Figures are whole-host measurements, not per-job attribution or browser-device telemetry.

```sh
python3 gpu_monitor.py dell-ts --output data/gpu-status.json
# Start the private workspace in a separate terminal after creating the SSH tunnel.
VERSIONBRIDGE_INFERENCE_MODE=local-gpu \
VERSIONBRIDGE_OLLAMA_PORT=11436 \
VERSIONBRIDGE_LOCAL_OUTPUT=800 \
VERSIONBRIDGE_GPU_STATUS_FILE=data/gpu-status.json \
ENABLE_JOB_QUEUE=1 python3 server.py
```

Quiet mode still requires fresh readings, temperature below 65 C, utilization below 30%, and at least 1536 MiB free before admission. It can pause requests; it does not claim to control hardware cooling or impose a GPU power limit. Ollama unload-on-response remains enabled.

## Reproduce QA

```sh
docker build -t versionbridge-sandbox:1 -f Sandbox.Dockerfile .
python3 smoke.py
python3 api_smoke.py
python3 -m unittest test_v2 test_v2_sandbox -v
node --check web/app.js
node --check web/resources.js
# Live model evaluation consumes inference allowance:
python3 evaluate_v2.py --models glm-5.3-flash deepseek-v4.1-flash-1017 --output v2-evaluation.json
```

The evaluation scoreboard records category, served models, verified rate, known false acceptance, latency and reserved inference cost. Model routing remains based on the tested primary/fallback pair, not an unearned category score. Cost reservations are not provider invoices or a $200 account-wide spending cap.
