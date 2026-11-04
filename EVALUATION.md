# Acceptance and model evaluation

Run `docker build -t versionbridge-sandbox:1 -f Sandbox.Dockerfile .`, then `python3 smoke.py`. The same smoke suite runs in GitHub Actions.

| Case | Baseline | Expected candidate outcome |
| --- | --- | --- |
| pandas 2 migration | Two failures after removal of DataFrame.append | Two passes after switching to concat |
| Pydantic settings | Two failures after BaseSettings moved | Two passes, including an environment override |
| Invoice arithmetic | Four wrong totals on the original formula | The model can author a bounded expression that passes all four cases |
| Regression guard | Standard DataFrame fails, legacy adapter preserves audit metadata | The standard frame works but the adapter loses audit metadata, so the verifier rejects the patch |
| Containment | Real network and filesystem attempts, a live infinite loop, and kernel memory-limit inspection | Restrictions observed and Docker confirms each container is gone |

For a real GitHub import without using the repository that contains all three fixtures, paste the public VersionBridge repository URL and pin ref `274b7ba6ec8fd8d418f686f37538517d4f87ca82` with the pandas profile. That immutable revision contains only the original pandas fixture. Public import is opt-in.

For a live provider comparison, check the model IDs available to your Vultr account, set `VULTR_API_KEY` through the service environment, and run:

```sh
python3 evaluate_models.py qwen2.5-coder-32b-instruct SECOND_AVAILABLE_MODEL > model-evidence.json
```

Each model sees the same four tasks. The script ranks correct observed outcomes first, then total elapsed time. Provider errors, missing evidence and false acceptance of the regression count against the model. This comparison uses real inference requests and can consume credits. The fixtures check this repair workflow and do not establish general model quality.
