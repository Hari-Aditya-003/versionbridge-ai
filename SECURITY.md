# Execution security

Only the control plane reads the Vultr inference key. The sandbox is a disposable process boundary with a non-root user, no network, a read-only root filesystem and source mount, bounded temporary storage, no elevated capabilities, CPU and memory limits, a PID cap and a deadline. Docker removes the container on exit and the control plane checks that it is gone. The Containment Lab exercises network, filesystem, deadline and memory policy.

Source and test output can carry prompt injection. The model receives no execution tools. Python policy checks constrain the edit, and the controller owns the test command, sandbox settings, test artifacts and verification status. The arithmetic parser builds a syntax tree and never evaluates it in the control plane. The allowed expression runs only in the sandbox.

A repository can supply misleading tests or print fabricated output. Imported results therefore describe the behavior of that repository's supplied tests and runtime. Use the controlled fixtures for reproducible judge evidence. Keep public imports off on the shared demo unless the dedicated worker environment has been hardened and tested. See the [deployment notes](deploy/README.md) for rate limits and secret handling.
