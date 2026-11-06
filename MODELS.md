# Model selection and verification

VersionBridge uses a model to propose a repair for a reproduced supported failure. The backend constrains the proposed edit and runs the same tests before and after the change. A model's reasoning helps explain the patch. A passing verification run supplies the evidence.

## Vultr judging profile

The deployed model is `glm-5.3-flash`. It achieved all 13 expected outcomes in the recorded comparison, including regression rejection. `deepseek-v4.1-flash-1017` achieved 12 of 13. The comparison uses the same controlled profiles, proposal limit, and verification gates for both candidates. [Vultr model catalog](https://api.vultrinference.com/docs/models) · [Recorded comparison](EVALUATION.md)

| What to compare | Evidence |
| --- | --- |
| Correct repairs | Expected outcome of each fixture, baseline and verification exit codes, and diff |
| Regression protection | The seeded audit metadata regression is rejected |
| Resource use | Elapsed time and token usage when returned by the provider |
| Model attribution | Requested and served model, provider completion ID, and attempt count when available |

The evaluation command covers supported profile cases, allows at most two patch attempts per case, and accepts up to three models. It sorts by correct outcomes and then elapsed time. Treat this as an evaluation of the supported workflow and fixtures. Acceptance tests use labeled sample patches. The published model comparison and hosted run use authenticated Vultr inference. [Evaluation and commands](EVALUATION.md)

Keep model calls for the judged application on Vultr Serverless Inference. The private Ollama mode uses a quantized Qwen2.5 Coder 1.5B model on a trusted Dell. It is a separate development profile. [Private Dell setup](LOCAL_GPU.md). [LabLab Blast Radius Zero rules](https://lablab.ai/ai-hackathons/vultr-hackathon/)

## Comparable projects

- AegisPR compares test behavior across PR revisions, publishes bounded model receipts, and uses CUDA to rank context separately from remote Nemotron calls. VersionBridge verifies a scoped patch by rerunning the repository's existing tests. [AegisPR](https://github.com/Hari-Aditya-003/AegisPR) · [Project comparison](COMPARISON.md)
- ARCHON reports individual repair attempts, acceptance outcomes and costs. VersionBridge follows that evidence pattern by pairing each candidate with a diff, test outputs, and provider information when available. [ARCHON](https://github.com/CodeWithEugene/Archon)
- AgentForge AI illustrates a bounded repair loop with human review. Agent CrashLab records executed assertions and scenario inputs. VersionBridge gives the maintainer a patch to review and exposes the observed failure that led to rejection. [AgentForge AI](https://devpost.com/software/agentforge-ai-yoif19) · [Agent CrashLab](https://devpost.com/software/agent-crashlab)

## Observed release selection

The November 5 comparison selected `glm-5.3-flash` after all 13 fixture outcomes matched expectations. `deepseek-v4.1-flash-1017` achieved 12 of 13. The requests used structured JSON, minimal reasoning effort, bounded output, and up to two proposals per case. Larger reasoning budgets should be evaluated separately before changing the deployed request policy. [Recorded comparison](EVALUATION.md)
