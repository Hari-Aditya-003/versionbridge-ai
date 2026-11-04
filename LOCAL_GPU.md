# Private Dell inference

VersionBridge can use an Ollama instance on a trusted Dell through an SSH tunnel. The Dell runs inference. The application host runs the Python orchestrator and its separate Docker test sandboxes. Use the [Vultr configuration](deploy/README.md) for the public hackathon deployment.

The default local model is Qwen2.5 Coder 1.5B Instruct Q4_K_M. Its quantized weights are 986 MB. The app sends one short request at a time and requests a 2,048-token context, a maximum of 320 generated tokens, two CPU threads, and unloading after each response. The app reports Ollama as the provider. Confirm GPU placement separately through the Ollama logs or NVIDIA telemetry. [Ollama model card](https://ollama.com/library/qwen2.5-coder:1.5b-instruct-q4_K_M)

On the Dell, start an Ollama service bound to loopback and pull the model. For a portable Ollama installation use its absolute executable path.

```sh
OLLAMA_HOST=127.0.0.1:11435 OLLAMA_NUM_PARALLEL=1 OLLAMA_MAX_LOADED_MODELS=1 \
  OLLAMA_MAX_QUEUE=1 nice -n 10 ollama serve
# Run from a second Dell terminal against the same service.
OLLAMA_HOST=127.0.0.1:11435 ollama pull qwen2.5-coder:1.5b-instruct-q4_K_M
```

On the application host, forward a loopback port to the Dell and start VersionBridge in a second terminal. Replace the SSH alias if needed.

```sh
ssh -NT -o ExitOnForwardFailure=yes -L 127.0.0.1:11435:127.0.0.1:11435 dell-ts
```

```sh
docker build -f Sandbox.Dockerfile -t versionbridge-sandbox:1 .
VERSIONBRIDGE_INFERENCE_MODE=local-gpu VERSIONBRIDGE_OLLAMA_PORT=11435 python3 server.py
```

The demo labels proposals with the provider and requested model. Each patch still has to pass the unchanged tests in a new sandbox. Add `ENABLE_PUBLIC_IMPORT=1 ENABLE_SCOPED_REPAIR=1` for a private trial of scoped Python repair. Enter the public repository, pinned commit, Python file path, and top-level function. The target function must have a single return statement. The candidate can use its named arguments, small integer constants, and addition, subtraction or multiplication. Imported tests and source must fit the prebuilt sandbox image.

To stop inference, end the Dell service and SSH forwarding sessions. Set `REQUIRE_INFERENCE=1` on the Vultr deployment to require Vultr and reject local mode.
