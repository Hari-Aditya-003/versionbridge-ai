# VersionBridge AI LabLab submission kit

- **Track** — Blast Radius Zero, sandboxed code execution
- **Tagline** — When dependencies break, prove the fix.
- **Source** — https://github.com/Hari-Aditya-003/versionbridge-ai
- **License** — MIT

## Short description

VersionBridge AI reproduces Python bugs and dependency failures, proposes a targeted repair, and reruns the original tests in a fresh sandbox. Reviewers can inspect what changed, which tests passed, and whether each container was removed.

## Project description

Dependency upgrades can break code far from the version change. VersionBridge resolves an immutable public GitHub snapshot or loads a controlled example, captures a baseline failure, and routes the relevant source and test output to a coding model. The sandbox runs the same suite after applying the candidate patch to a temporary copy. If the tests still fail, the agent can use the failure to try a second candidate. The evidence report records the outcomes and leaves the decision to apply the patch with the maintainer.

The judge demo walks through a pandas repair, a Pydantic migration, an invoice bug, and a patch rejected for dropping audit metadata. The Containment Lab shows denied network and filesystem operations, a forced timeout, the kernel memory cap, and teardown.

## Judge access and evidence

| Item | State |
| --- | --- |
| Public licensed source | Published |
| Credential-free local Docker build | [README](README.md) |
| Case definitions and model comparison | [Evaluation](EVALUATION.md) |
| Architecture and security | [Architecture](ARCHITECTURE.md), [Security](SECURITY.md) |
| Cover artwork | [VersionBridge brand artwork](web/brand.png) |
| Live Vultr model receipt | Pending authorized inference access |
| Public HTTPS app on a Vultr VM | Pending deployment and external verification |
| Final video | Capture the public deployment following [the demo script](DEMO.md) |
| Slides | Use the outline below after recording verified Vultr results |
| LabLab submission | Pending public URL, video, presentation and final review |

## Presentation outline

1. The problem — A library upgrade breaks a production workflow and the failing code is unclear.
2. The product — Show a real GitHub commit, baseline failure, diagnosis, and candidate patch.
3. The verification — Show the fresh verification container, the same test suite, and the rejected audit-metadata regression.
4. Vultr architecture — Identify the VM, Serverless Inference model, container boundary and stored evidence.
5. Containment and impact — Show an actual deadline and teardown, then explain how maintainers can review and apply the patch.

Use the [official LabLab requirements](https://lablab.ai/ai-hackathons/vultr-hackathon/) for the final submission.
