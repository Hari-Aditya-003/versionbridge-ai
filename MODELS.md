# Model selection and verification

VersionBridge uses a model to propose a repair for a reproduced Python failure. The backend constrains the proposed edit and runs the same tests before and after the change. A model's reasoning helps explain the patch. A passing verification run supplies the evidence.

## Vultr judging profile

Use the model IDs shown in the Vultr account's console. DeepSeek V4.1 Flash 1017 is the current configured candidate. Compare GLM 5.3 Flash on the same cases before selecting a deployment model. Choose the deployment model after measuring the same repair and regression cases across the candidates. [Vultr coding model list](https://docs.vultr.com/support/products/serverless/can-i-run-inference-workloads-for-models-other-than-llms-on-vultr-serverless-inference) · [Vultr model overview](https://docs.vultr.com/product-overviews/serverless-inference)

| What to compare | Evidence |
| --- | --- |
| Correct repairs | Expected outcome of each fixture, baseline and verification exit codes, and diff |
| Regression protection | The seeded audit metadata regression is rejected |
| Resource use | Elapsed time and token usage when returned by the provider |
| Model attribution | Requested and served model, provider completion ID, and attempt count when available |

The evaluation command covers supported profile cases, allows at most two patch attempts per case, and accepts up to three models. It sorts by correct outcomes and then elapsed time. Treat this as an evaluation of the supported workflow and fixtures. The current local test and demo evidence uses labeled sample patches. Authenticated comparison results and a production model choice are pending. [Evaluation and commands](EVALUATION.md)

Keep model calls for the judged application on Vultr Serverless Inference. The private Ollama mode uses a quantized Qwen2.5 Coder 1.5B model on a trusted Dell. It is a separate development profile. [Private Dell setup](LOCAL_GPU.md). [LabLab Blast Radius Zero rules](https://lablab.ai/ai-hackathons/vultr-hackathon/)

## Comparable projects

- AegisPR compares test behavior across PR revisions, publishes bounded model receipts, and uses CUDA to rank context separately from remote Nemotron calls. VersionBridge verifies a scoped patch by rerunning the repository's existing tests. [AegisPR](https://github.com/Hari-Aditya-003/AegisPR) · [Project comparison](COMPARISON.md)
- ARCHON reports individual repair attempts, acceptance outcomes and costs. VersionBridge follows that evidence pattern by pairing each candidate with a diff, test outputs, and provider information when available. [ARCHON](https://github.com/CodeWithEugene/Archon)
- AgentForge AI illustrates a bounded repair loop with human review. Agent CrashLab records executed assertions and scenario inputs. VersionBridge gives the maintainer a patch to review and exposes the observed failure that led to rejection. [AgentForge AI](https://devpost.com/software/agentforge-ai-yoif19) · [Agent CrashLab](https://devpost.com/software/agent-crashlab)
