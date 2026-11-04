# Record the VersionBridge demo

Record the public Vultr deployment in a 16:9 browser window. Open the demo in its own tab from the homepage. Start with a fresh run, then keep the unedited test and containment results on screen long enough to read.

| Time | On screen | Narration cue |
| --- | --- | --- |
| 0:00–0:12 | Landing page and repair workspace | A Python upgrade removed the API this project uses. VersionBridge reproduces the failure and checks the fix against the same tests. |
| 0:12–0:42 | Run repair and follow the live sandbox activity | Point to the baseline container ID, failing pytest output, Vultr model name, and new verification container ID. |
| 0:42–1:05 | Open the diff and evidence download | Show the one-line change and the passing pytest result. The export contains exit codes, checksums and container lifecycle events. |
| 1:05–1:42 | Run the Containment Lab | Show blocked network and filesystem access, then wait for the infinite loop deadline. Point to the recorded teardown and the kernel memory cap. |
| 1:42–2:00 | Architecture and GitHub link | The control plane runs on Vultr Cloud Compute, the model runs on Vultr Serverless Inference, and execution happens in disposable containers. |

Use a local recording for rehearsal. For the submission capture, confirm that the browser address and the verified run show your public Vultr deployment and live model.
