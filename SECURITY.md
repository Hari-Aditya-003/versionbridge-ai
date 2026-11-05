# Execution security

Only the control plane reads the Vultr inference key. The sandbox is a disposable process boundary with a non-root user, no network, a read-only root filesystem and source mount, bounded temporary storage, no elevated capabilities, CPU and memory limits, a PID cap and a deadline. Docker removes the container on exit and the control plane checks that it is gone. The Containment Lab exercises network, filesystem, deadline and memory policy.

Source and test output can carry prompt injection. The model receives no execution tools. Python policy checks constrain the edit, and the controller owns the test command, sandbox settings, test artifacts and verification status. The arithmetic parser builds a syntax tree and never evaluates it in the control plane. For an imported scoped repair, the controller permits one return expression in a named top-level application function. It rejects test files, calls and attributes in the replacement. Pytest starts in isolated Python mode with third-party plugin autoload disabled. The allowed expression runs only in the sandbox.

A repository can supply misleading tests or print fabricated output. Imported results therefore describe the behavior of that repository's supplied tests and runtime. Use the controlled fixtures for reproducible judge evidence. Keep public imports off on the shared demo unless the dedicated worker environment has been hardened and tested. See the [deployment notes](deploy/README.md) for rate limits and secret handling.

The structured pytest report adds a check for missing tests and changed skips. Code running inside the container can influence that report. Treat imported outcomes as evidence from the supplied suite. Keep the optional job queue private until requests and artifacts can be tied to authenticated users.

## Production process boundary

The installer runs the HTTP API as `versionbridge-web` and the worker as `versionbridge-worker`. Only the worker joins the Docker group and receives inference credentials. Both can access the group-private SQLite directory. Docker control remains a privileged capability on the VM, so this boundary reduces direct exposure without proving resistance to a compromised worker.

The optional private access token gates API data and execution requests. Public mode disables repository imports and permits only the curated workloads. A persistent daily submission quota and separate paid-inference allowance limit repeated execution. The application is a single-workspace release and does not claim tenant isolation.

Compiler workloads need bounded executable scratch space. The native profiles use an additional tmpfs for their compiled program. The normal scratch mount remains non-executable. PostgreSQL uses a local Unix socket inside its container and disposable fixture data.
