# VersionBridge product walkthrough

[Watch the silent walkthrough](https://hari-aditya-003.github.io/versionbridge-ai/demo.html) · [MP4](showcase/versionbridge-final-walkthrough.mp4) · [Narration text](showcase/VersionBridge-Audio-Script.txt) · [Capture record](showcase/final-walkthrough-capture.json)

The November 7 walkthrough uses the working public application at https://versionbridge.pages.dev/. It has no audio track. It shows:

1. The homepage and interactive animated architecture.
2. Repair profiles and their verification contracts.
3. A real two-file Python migration using GLM 5.3 Flash through Vultr inference.
4. The live workflow, failing baseline and passing candidate output.
5. Original/candidate source snapshots, container commands and resource limits.
6. Passing original tests, independent checks, patch review and TXT export.
7. A harmful patch rejected by the original regression tests.
8. Network, filesystem, deadline and memory containment checks with container cleanup.
9. Whole-host resource readings and explicit unavailable GPU sensors.

The video combines selected live tutorial runs. Static gaps between captured frames are capped at two seconds. Responsive browser views are letterboxed without cropping. The execution results are unchanged. One earlier negative-case take was excluded after its optional fallback provider returned an invalid structured response; it failed closed and is recorded in the capture metadata. The included negative case uses one bounded attempt and is rejected by the test gate.

[Live QA evidence](evidence/product-live-qa-2026-11-07.json) · [Actual downloaded TXT bundle](evidence/walkthrough-run.txt) · [How to use VersionBridge](USER_GUIDE.md)

For another walkthrough, first rehearse the controls and confirm the workspace has finished loading its configuration. Record a fresh repair, inspect its evidence, demonstrate a rejected regression and then run containment. Preserve the actual outcomes, including any error; do not present a rehearsed or sample run as live model inference.
