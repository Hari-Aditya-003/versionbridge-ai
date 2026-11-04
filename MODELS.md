# Model selection and verification

The hackathon build sends all agent model calls to Vultr Serverless Inference. Start with Qwen2.5 Coder 32B as a documented coding baseline. Compare it with DeepSeek V4.1 Flash and GLM 5.2 if those models are available in the account. Confirm the exact identifiers in the Vultr Console before running the comparison. These are candidates. A benchmark winner requires live results on the same fixtures.

Rank models by correct verified outcomes and rejection of the seeded regression, then by elapsed time. Record token use when the provider reports it. Each proposal can retain the requested and served model, completion ID and token usage. Keep benchmark requests bounded to four cases, two attempts per case and up to three models. See [evaluation instructions](EVALUATION.md).

The Dell GPU, AMD Developer Cloud, and Nebius Token Factory credits can support separate experiments. Keep them outside the judged VersionBridge runtime because Blast Radius Zero requires Vultr for the agent's model calls and deployment. The control plane and Docker fixtures do not need GPU compute.

## Comparable projects

- [AegisPR](https://github.com/Hari-Aditya-003/AegisPR) separates deterministic test evidence from model intent judgments and labels its local and live runs individually.
- [ARCHON](https://github.com/CodeWithEugene/Archon) publishes reproducible instance-level repair results, failed attempts, and bounded costs. Its results are reported by the project.
- [AgentForge AI](https://devpost.com/software/agentforge-ai-yoif19) illustrates a bounded test-and-repair loop with evidence and human review.
- [Agent CrashLab](https://devpost.com/software/agent-crashlab) records scenario seeds and executed assertions, so a reviewer can reconstruct why a repair passed or failed.

Sources: [Vultr model overview](https://docs.vultr.com/product-overviews/serverless-inference), [Vultr coding model list](https://docs.vultr.com/support/products/serverless/can-i-run-inference-workloads-for-models-other-than-llms-on-vultr-serverless-inference), [LabLab rules](https://lablab.ai/ai-hackathons/vultr-hackathon).
