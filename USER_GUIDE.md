# VersionBridge AI user guide

VersionBridge helps maintainers investigate broken code and dependency upgrades. It reproduces the failure, proposes a restricted change, checks it in fresh containers, and records evidence for review.

## Start a repair

1. Open [VersionBridge](https://versionbridge.pages.dev/), then choose **Run the demo**. The workspace opens separately.
2. Choose a repair profile. AI-authored Python migrations allow the model to write scoped edits without a replacement answer list. Reviewed language/database examples use narrower policies. Read the profile card for the exact source and checks.
3. Select one or two attempts and choose **Run repair**. The live workflow follows actual recorded execution events.
4. Watch **Sandbox activity**. Output appears while the container runs. **Open sandbox** opens the read-only Console, Run files, and Container details inspector.
5. Compare the original and candidate tests, independent checks when available, and the patch. A rejected or inconclusive run is not a verified repair.
6. After execution, choose **Save run files · TXT** to download scoped source snapshots, results and captured output. JSON, Markdown and verified patch downloads remain available.

The public workspace uses reviewed source projects and one exact pinned GitHub example. It is not an arbitrary-repository repair service. General repository adapters and private organization features remain in the [implementation map](V2_IMPLEMENTATION.md).

## Inspect the architecture

Select any node on the homepage architecture to read its responsibility. The animation illustrates the final design; it is labelled as a guide. The workspace's separate graph follows actual job events. Cloud and private Dell models share the same trusted patch policy and verification rules.

## Inspect containment

Run the Containment Lab to observe network denial, filesystem protection, non-root execution, memory limits, deadline enforcement and container removal. The same inspector and TXT export are available for that run.

## Read system resources

The compact resource panel shows whole application-host RAM/CPU and accessible GPU readings. Expand it for clock and memory details. Hosted inference GPU readings are unavailable when the provider does not expose sensors. The temperature row is intentionally omitted. These figures are not per-job attribution.

## Review and apply

A passing result means verified against its listed checks. Inspect the evidence and make the final decision to apply the downloaded patch. VersionBridge does not automatically merge a change into your repository.
