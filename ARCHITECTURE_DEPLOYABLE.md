# VersionBridge AI — Final Dual-Backend Architecture Specification
Date: 2026-11-06
Status: **target design**. This document describes the intended V2 system, not a claim that every module already exists.

## Executive decision

Build an **adaptive, category-aware, evidence-first repair pipeline**, with a single orchestrator and verification engine and two swappable inference backends:
1. **Cloud/Vultr**: the judged Blast Radius Zero path, using available Vultr Serverless Inference models and Docker execution on a Vultr VM.
2. **Private/local Dell GPU**: Ollama through loopback/SSH forwarding using small quantized models and the same patch validation/verification semantics.

**Default to a sequential model cascade, not four models in parallel.** Allow small concurrent candidate pools only after measuring cost, worker capacity, and value added. A reviewer model can advise but **cannot override failed tests or policy gates**.

## Current implementation vs proposed work

| Component | Main branch baseline | V2 disposition |
| --- | --- | --- |
| API, persistence and job recovery | Exists in server.py, jobs.py, history.py, worker.py | Keep and extend |
| Fresh bounded Docker sandboxes | Exists | Keep; harden untrusted import isolation |
| Curated one-line repair profiles | Exists | Preserve as compatibility and demonstration mode |
| Test inventory, pass/fail and hashes | Exists | Keep; augment independent tests |
| Vultr inference | Exists | Add catalog-aware model registry and category router |
| Local private Ollama mode | Exists; 1.5B default, 2K context | Add resource-aware model selection |
| Two-model verification retry | Implemented opt-in in PR #1 branch | Test, measure and review before merge |
| Five-category routing | Not implemented | Build |
| Full AST/call-graph indexing | Not implemented | Build incrementally |
| Open-ended, multi-file migration | Not implemented | Requires new safe patch engine |
| Generated independent regression tests | Not implemented | Add only after immutable baseline trust boundary |
| LLM critic / multi-agent voting | Not implemented | Optional advisory role, never judge of record |
| Autonomous PR creation and signing | Not implemented | Later; human approval, signing infrastructure |

## Proposed architecture

~~~mermaid
flowchart TD
    UI[Browser Workspace / GitHub import] --> API[API + durable job queue]
    API --> Intake[0. Pin SHA, inventory source and dependency versions]
    Intake --> Base[1. Fresh baseline sandbox + test inventory]
    Base --> Analyze[2. Classification / fault localization / retrieval]
    Analyze --> Route[3. Category router + budget-aware model registry]
    Route --> Infer{Inference backend}
    Infer --> Cloud[Vultr Serverless model adapter]
    Infer --> Local[Ollama SSH loopback adapter]
    Cloud --> Candidate[4. Structured repair candidates]
    Local --> Candidate
    Candidate --> Policy[5. Deterministic patch / syntax / immutability gate]
    Policy -->|rejected| Reject[Record rejection evidence]
    Policy -->|accepted| Run[6. Fresh candidate Docker sandbox]
    Run --> Verify[Test / static / regression / optional property checks]
    Verify -->|fails; attempts remain| Retry[Targeted repair feedback + different model]
    Retry --> Route
    Verify -->|passes| Review[Optional independent model critic; advisory only]
    Review --> Result[Verified against specified checks + human review]
    Reject --> Report[Evidence store / receipts / diff / logs]
    Result --> Report
    Report --> UI
~~~

Sandbox authority never flows into the model or API process. Only the worker performs bounded execution. The model receives **untrusted context**, not tools or host credentials.

## Working principle: six primary phases (plus intake and export)

### Phase 0 — Intake and reproducibility
- Accept only a pinned, size-limited repository snapshot; record source commit, resolved dependencies and immutable image digest.
- Read manifests/lockfiles safely without execution. Produce SBOM where supported and a test file SHA-256 inventory.
- Prepare offline dependencies in a separately governed acquisition step, **never with unrestricted network inside the test sandbox**.
- For public shared deployments, keep arbitrary repository imports disabled until stronger isolation is assessed.

### Phase 1 — Baseline and fault localization
- Execute the exact original project test/build command in a fresh sandbox with strict resource limits.
- Parse stack traces, compiler diagnostics, file references, error codes, and test identifiers.
- Build AST/symbol/import relationships; return source locations and certainty for each inferred edge.
- Select relevant evidence with deterministic file/path limits and retrieval, rather than sending the whole repository.

### Phase 2 — Diagnostic category router
Five tracks:
1. **API/library migration**: removed method, moved import, signature/default change, dependency version mismatch.
2. **Algorithmic/arithmetic logic**: failing invariants, bounds, integer and state logic.
3. **Type/compiled build**: TypeScript, Go, Rust, Java, C++ compiler/type diagnostics.
4. **SQL/schema/query behavior**: NULLs, joins, migrations, precision, transaction and rollback behavior.
5. **Regression/security audit**: state loss, test skipping, policy bypass, untrusted-input risks.

Use deterministic signals first (traceback signatures, syntax and compiler errors, manifest diff, tool findings). Ask a cheap LLM classifier only if ambiguous. The five tracks are **routing labels**, not mutually exclusive safety boundaries; regression and security gates run for every track. Record mixed/unknown classifications rather than forcing a false category.

### Phase 3 — Model selection and repair planning
- Select primary and fallback candidates from a **validated model registry**, filtered by provider, context capacity, JSON support, cost and measured per-category holdout performance.
- Prefer a capable affordable generator on attempt 1. If verification fails, send limited failure feedback to a different model family on attempt 2; optional third attempt only when explicitly configured and budget allows.
- Model roles: planner/root cause, repair writer, optional alternative writer, optional independent critic. These roles do not require four distinct models per job.
- Model output must include diagnosis, affected files, intent and a scoped edit manifest. No free-form shell commands or modifications to tests.
- Maintain independent per-stage provider receipts: requested ID, served ID, latency, token usage, budget reservation and model response identifier.

### Phase 4 — Structural patch and security policy
- Default first implementation: a *single source file* with allowed AST edits; expand to allowlisted multi-file import/call-site migration only after test coverage is ready.
- Validate edit manifest, UTF-8, path normalization, file/line/byte caps, diff applicability, syntax/compilation, forbidden directories and no test/config/security policy weakening.
- Reject changes to tests, fixtures, workflow security settings and dependency constraints unless a separately reviewed migration policy explicitly permits them.
- Run Semgrep/CodeQL/OSV-Scanner as complementary analyses where installed, but do not treat a clean scan as proof of security.
- Discard the model proposal and record a rejection if policy fails. No model can self-approve.

### Phase 5 — Isolated candidate verification
- Apply each candidate to a **fresh copy of the original pinned source**, not a mutated previous candidate tree.
- Execute the original test command with the same test inventory and image; require baseline failure -> candidate pass and unchanged skip/expected-failure semantics.
- Check process exit code and timeout, then compiler/linter/security findings and independent relevant tests when available.
- Add differential testing, Hypothesis/property-based tests, migration rollback scenarios, and mutation testing as per-language adapters become mature.
- Sandbox concurrency must be resource-budgeted. Default **one active candidate at a time** on the Dell; bounded parallel workers may run on Vultr after resource measurement.
- A flaky or incomplete result is **UNVERIFIED**, never a success.

### Phase 6 — Evidence ranking and export
- Eligibility is binary: policy and required executed checks must pass. An LLM vote cannot change eligibility.
- Among eligible candidates, prefer lower regression risk, smaller focused diff, fewer newly triggered findings and lower measured resources; tie-break with independent critique if justified.
- Produce diff, source/policy/test hashes, package versions, build and test outputs, attempt history, model receipts, sandbox teardown evidence and human-review status.
- A label of VERIFIED means verified **against the listed checks only**, never formally proven correct. Signed PR diffs require a separate signing key and process.
- Human reviews and approves proposed GitHub changes; automatic PR submission comes later.

## Cloud vs local deployment matrix

| Topic | Vultr cloud target | Dell local target |
| --- | --- | --- |
| Orchestrator | Python API and worker on Vultr VM | Same Python API and worker |
| Model calls | Vultr Serverless Inference endpoint | Private Ollama over 127.0.0.1 / SSH tunnel |
| Default generator | GLM 5.3 Flash (recorded V1 success) | Qwen2.5-Coder 3B Q4 candidate; V1 stable 1.5B fallback |
| Fallback | DeepSeek V4.1 Flash 1017 (recorded V1 comparison) | DeepSeek-R1 1.5B Q4 for optional critique; evaluate effectiveness |
| Model parallelism | 1 default; only bounded speculative k=2 after measured gain | 1 loaded model, one inference at a time |
| Context policy | Truncate/retrieve against chosen model limit | Begin with 2,048–4,096 tokens; raise only if telemetry allows |
| Test execution | Sandboxed Docker on Vultr VM | Sandboxed Docker on trusted Linux host |
| Developer workflow | Public judges' demo, receipts, downloadable patch | Private development, offline experiments |
| Network | Host calls Vultr inference; sandbox has no network | SSH loopback to Dell; sandbox has no network |
| Credentials | Worker-only API key | No provider key in sandbox; Ollama bound to loopback |

### Model selection rules

Do **not** hardcode screenshot SOTA model names as provider-guaranteed. They are candidates for benchmarking only. Cloud categories can initially share the same two known working IDs while collecting per-category performance evidence. Add a specialized model only when it exists in the actual provider catalog and beats the incumbent on held-out tasks.

**Important Vultr API behavior:** unknown plain chat model IDs can silently resolve to a default model. At startup, query the public model catalog at https://api.vultrinference.com/v1/models; verify ID availability and needed parameters. After inference, require a recorded served-model ID and flag model substitution rather than counting it as a requested-model result. See https://api.vultrinference.com/docs/get-started/quickstart.

**Important local sizing:** Ollama's listed Qwen2.5-Coder 3B quantized download is about 1.9 GB, DeepSeek-R1 1.5B is about 1.1 GB, while Qwen2.5-Coder 7B is about 4.7 GB before context/runtime overhead. A 7B model should **not be the default** on the Dell RTX 3050 Ti 4 GB. Keep MAX_LOADED_MODELS=1 and unload between different models. Watch GPU telemetry and benchmark context length.

The Linux RTX 5070 Ti 16GB workstation, if used separately, could support a larger **private** model profile after memory/latency testing; it is not the default Dell profile or part of the judged Vultr path.

## Initial category-to-model routing policy (proposed)

These are **starting configurations, not per-category SOTA claims**. The initial Vultr provider pool is based on models recorded in the V1 evidence, and the local choices are constrained by the Dell's GPU memory. The router must replace these defaults with benchmark-backed decisions only after per-category holdout scores exist.

| Failure category | Vultr primary / fallback | Dell Ollama initial roles | Non-LLM authority |
| --- | --- | --- | --- |
| API / library migration | GLM 5.3 Flash → DeepSeek V4.1 Flash 1017 | Qwen2.5-Coder 3B; optional DeepSeek-R1 1.5B feedback | Version-pinned docs, import checks, baseline and regression tests |
| Algorithmic / arithmetic | GLM 5.3 Flash → DeepSeek V4.1 Flash 1017 | DeepSeek-R1 1.5B for concise diagnosis, Qwen2.5-Coder 3B for patch | Property-based invariants and executed tests |
| Type / compiled build | GLM 5.3 Flash → DeepSeek V4.1 Flash 1017 | Qwen2.5-Coder 3B for proposals | Actual compiler/type checker diagnostics |
| SQL / schema | GLM 5.3 Flash → DeepSeek V4.1 Flash 1017 | Qwen2.5-Coder 3B with small schema excerpts | Disposable DB query results, constraints, rollback tests |
| Regression / security | No model can override the deterministic gate; optional advisory review with a different served model | Optional DeepSeek-R1 1.5B advisory | Immutable test set, policy checks, containment probes |

For compiled-language and SQL categories, models create proposals; they never substitute for actual compilation or database execution. If a local model cannot fit or cannot produce a schema-valid proposal, mark the attempt unverified rather than silently falling back to an arbitrary heavyweight model.

## Implementation modules and responsibility map

### Reuse existing files (implemented)
| Existing module | Responsibility |
| --- | --- |
| server.py | Web API and current orchestrator/sandbox |
| worker.py / jobs.py / history.py | Worker dispatch, queue, history and evidence |
| inference.py / budget.py | Vultr inference and paid allowance |
| local_gpu.py / gpu_guard.py / gpu_monitor.py | Ollama transport, optional GPU admission checks |
| model_routing.py (PR #1 only) | Opt-in two-model sequential retry routing |
| inspection.py / projects.py | Metadata inventory and pinned snapshot retrieval |
| profiles.py / python_target.py | Curated policies and scoped Python targets |
| pytest_runner.py / verification.py | Test inventory and regression gate |
| reports.py | Portable evidence report |
| evaluate_models.py / smoke.py / api_smoke.py | Model fixtures and integration verification |
| web/ | Existing workspace and showcase |

### Add these modules incrementally (NOT implemented)
| New module | Purpose | First milestone |
| --- | --- | --- |
| model_registry.py | Per-provider capabilities, ID validation, price and receipt policy | P1 |
| category_router.py | Deterministic five-track classification with ambiguity flags | P1 |
| evaluation_scoreboard.py | Per-category held-out scores and model selection | P1 |
| providers/base.py | Typed model request/response contract | P1 |
| providers/vultr.py | Vultr adapter and served-model verification | P1 |
| providers/ollama.py | Ollama adapter with memory constraints | P1 |
| context_builder.py | Traceback, AST, symbol context and token limits | P2 |
| migration_knowledge.py | Version-pinned local breaking-change documentation retrieval | P2 |
| language_adapters/ | Python, TS/JS, Go/Rust/Java/C++ and SQL test/build adapters | P2/P3 |
| patch_engine.py | Allowlisted AST/edit manifest and clean snapshot application | P2/P3 |
| policy_gate.py | No test tampering, path/size/syntax/security checks | P2 |
| candidate_scheduler.py | Budget-aware cascade and controlled parallel execution | P3 |
| critics.py | Optional independent advisory review | P3 |
| independent_tests.py | Property, differential and mutation testing | P3 |
| evidence_graph.py | Traceable source/dependency/call-site impact graph | P3 |
| web architecture panels | Category trace, candidate comparison, receipts and risk graph | P3 |

Suggested provider contract:

~~~text
ModelRequest {
  task_id, category, role, source_context, failure_evidence,
  allowed_files, schema_version, token_budget, cost_budget
}
ModelResponse {
  requested_model, served_model, provider, receipt, diagnosis,
  edits[], confidence_note, elapsed_ms, usage
}
RepairCandidate {
  candidate_id, source_commit, changed_files[], diff,
  policy_results[], verification_runs[], outcome
}
~~~

No model-supplied "confidence" is a correctness probability; calibrated confidence requires external measured validation.

## Operational configuration — examples, not all implemented

**Existing PR #1 cloud routing** (on PR branch, with two repair attempts):
~~~sh
# Worker only. Verify these IDs exist in your Vultr catalog first.
VULTR_API_KEY=... # use an environment secret, never commit
VULTR_MODEL=glm-5.3-flash
VULTR_MODEL_POOL=glm-5.3-flash,deepseek-v4.1-flash-1017
REQUIRE_INFERENCE=1
INFERENCE_BUDGET_USD=5
INFERENCE_DAILY_REQUESTS=30
~~~

**Existing private Dell mode**, documented in LOCAL_GPU.md:
~~~sh
# Ollama runs loopback on Dell and is forwarded through trusted SSH.
VERSIONBRIDGE_INFERENCE_MODE=local-gpu
VERSIONBRIDGE_OLLAMA_PORT=11435
VERSIONBRIDGE_LOCAL_MODEL=qwen2.5-coder:1.5b-instruct-q4_K_M
~~~
The 3B upgrade and configurable 4K/8K context are **future changes to local_gpu.py**, not supported tunables in the present source. The current source explicitly requests num_ctx=2048, num_predict=320, and keep_alive=0.

**Planned V2 configuration contract** (not currently recognized by the application):
~~~yaml
inference:
  mode: vultr  # or local
  strategy: cascade
  max_candidates: 2
  max_concurrent_candidates: 1
  enforce_served_model_match: true
routing:
  categories: [api_migration, algorithmic, compiled, sql, regression]
  low_confidence_fallback: general_repair
security:
  immutable_test_inventory: true
  no_network_in_sandbox: true
  human_review_before_pr: true
~~~

## Validation plan and release gates

| Gate | Proof required |
| --- | --- |
| P0: Freeze V1 baseline | Record main SHA, fixture behavior, Docker image and evidence |
| P1: Cloud/local model registry and router | Unit tests, API smoke, sandbox smoke, live per-model receipt checks; no regressions |
| P2: Open-ended Python migrations | Held-out new migration examples without answer-key enums, policy tests, real execution |
| P3: Multi-file adapters + critics | Fresh baseline per candidate, cross-file tests, independent tests, false-acceptance study |
| P4: Public arbitrary repo import | Security review, stronger isolation, quotas, authenticated ownership and secrets audit |

Primary metrics: genuine resolved cases / total held-out cases, false-accept rate, test-weakening attempts blocked, changed-file localization precision/recall, candidate applicability, latency, actual and reserved inference cost, and sandbox containment failures. Track metrics separately by language and analysis category and compare against single-model V1. Public SWE-bench Verified scores alone are insufficient due to benchmark contamination concerns.

For the Nov 8, 2026 hackathon, prioritize stable Vultr execution, existing verified fixtures, credible receipts, and model-routing P1. Do not replace the judged environment with Dell inference. Treat open-ended multi-file repair and large MoA fan-out as post-submission research unless independently verified before submission.

## References and provider docs

- Existing V1 architecture: ARCHITECTURE.md, MODELS.md, EVALUATION.md and SECURITY.md.
- Vultr model catalog: https://api.vultrinference.com/v1/models
- Vultr chat and fallback behavior: https://api.vultrinference.com/docs/get-started/quickstart
- Ollama coder models: https://ollama.com/library/qwen2.5-coder
- Ollama reasoning models: https://ollama.com/library/deepseek-r1
- Tree-sitter: https://github.com/tree-sitter/tree-sitter
- OpenRewrite: https://github.com/openrewrite/rewrite
- Renovate: https://github.com/renovatebot/renovate
- Semgrep: https://github.com/semgrep/semgrep
- OSV-Scanner: https://github.com/google/osv-scanner
- Agentless localization/repair/validation: https://github.com/OpenAutoCoder/Agentless
- Hackathon: https://lablab.build/ai-hackathons/vultr-hackathon
