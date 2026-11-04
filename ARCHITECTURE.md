# Architecture

The browser submits a named repair profile and optional public GitHub reference. The Python control plane resolves imported source to a commit, checks for a unique supported edit, hashes the test files, and starts a disposable baseline container. It sends the bounded source and failure output to Vultr Serverless Inference. The model returns a diagnosis and one replacement line.

The controller validates the response against the profile policy. The invoice profile permits integer arithmetic over three known input names, with no calls or attributes. The migration profiles permit specific API replacements. A new container executes the original tests against the patched copy. If the candidate fails, the agent can receive the failed candidate and new test output in one follow-up request.

The baseline failure and candidate exit status determine the run outcome. The diagnosis remains advisory. Evidence includes the patch hash, test hash, attempt, provider receipt when present, sandbox IDs, teardown results, and Git commit when imported. The UI streams those events and persists repair runs in SQLite. The patch is applied only to the sandbox working copy and can be downloaded for review.
