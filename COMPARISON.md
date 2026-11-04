# AegisPR and VersionBridge AI

| Area | AegisPR | VersionBridge AI |
| --- | --- | --- |
| Primary question | Did this pull request change behavior or introduce a regression? | Can this supported Python failure be reproduced and repaired? |
| Input | A public GitHub pull request and its base/head revisions | A bundled fixture or a public repository at a pinned commit |
| Test approach | Can propose new tests and run them against base and head | Runs the same existing suite against the original snapshot and candidate patch |
| Agent model | NVIDIA Nemotron via Nebius Token Factory. AegisPR documents a live Nemotron 3 Super run. | Vultr Serverless Inference integration. Qwen2.5 Coder 32B is the configured default. The local demos use built-in sample patches. |
| Local ML or GPU | AegisPR documents optional Dell CUDA context ranking | No separate ML model, training pipeline, or GPU dependency |
| Shared capabilities | Isolated execution, repair proposals, repeatable evidence, and human review | Isolated execution, bounded repair proposals, repeatable evidence, and downloadable patches |
| Current gaps | See AegisPR's own submission materials for its judge deployment status | No PR base/head comparison, generated tests, GPU ranking, or general-purpose repair. Live Vultr model evidence and public Vultr deployment are pending. |

The local VersionBridge demo uses an actual public GitHub commit containing a deliberately seeded pandas fixture. It proves that GitHub retrieval, sandbox reproduction and patch verification work together. The fixture is a controlled example, so it does not measure repair performance across unrelated repositories.

[AegisPR source and live evidence](https://github.com/Hari-Aditya-003/AegisPR) · [VersionBridge evaluation](EVALUATION.md) · [VersionBridge model plan](MODELS.md)
