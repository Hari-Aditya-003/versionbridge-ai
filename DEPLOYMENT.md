# Deploy VersionBridge on Vultr

The deployment uses a dedicated Ubuntu 24.04 VM, Caddy for HTTPS, a web API without Docker privileges, and a separate execution worker. The worker alone receives the Vultr inference key. Public mode executes the curated examples and rejects arbitrary repository imports.

## Install

Clone a reviewed release into `/opt/versionbridge`, then run from that directory.

```sh
sudo bash deploy/install.sh YOUR_PUBLIC_HOSTNAME
```

The hostname must already resolve to the VM. The installer builds the sandbox image, creates service users, and enables Caddy and the two application services. Open inbound TCP 80 and 443. Restrict administrative SSH access as appropriate.

The installer initially uses labeled sample proposals. To enable judged live inference, edit the root-owned `/etc/versionbridge-worker.env` through a secure administrative session.

```text
REQUIRE_INFERENCE=1
VULTR_API_KEY=YOUR_SUBSCRIPTION_KEY
VULTR_MODEL=deepseek-v4.1-flash-1017
INFERENCE_BUDGET_USD=4
INFERENCE_DAILY_REQUESTS=30
```

Then restart `versionbridge-worker`. Set `REQUIRE_INFERENCE=1` in the web environment too, so the UI reports the configured provider mode. The web service must never receive the provider key.

## Verify

```sh
curl https://YOUR_PUBLIC_HOSTNAME/healthz
curl https://YOUR_PUBLIC_HOSTNAME/readyz
sudo systemctl status versionbridge-web versionbridge-worker caddy
sudo -u versionbridge-web docker info
```

The final command must fail with a Docker permission error. Check that only the worker belongs to the Docker group. Run a live repair, the regression rejection profile, and the Containment Lab through the public workspace. Export their reports and record the observed model, runtime, and teardown results.

## Budget

The selected development plan is one 2 GiB shared-CPU VM at $10/month, with backups at $2/month. Inference is usage-billed. Reserve $1 for local model evaluation and a separate $4 application allowance on the VM. These application reservations cover inference requests under the configured rate assumptions.

The $200 credit is the overall authorization ceiling. Application allowances do not enforce an account-wide Vultr cap. Review billing during development and destroy the VM when hosting is no longer needed. Stopping it does not stop resource billing. Other resources and account activity must be included in any total spending calculation.

## Operations

- Keep the shared state directory at mode 2770 with group `versionbridge`.
- Keep both environment files root-owned at mode 0600.
- Use one worker per database. Its process lock prevents duplicates.
- Review `journalctl -u versionbridge-worker` for task errors.
- After deployment updates, rebuild the sandbox and restart both services.
- Back up `/var/lib/versionbridge/runs.sqlite3` using SQLite's backup mechanism before restoring state or rolling back.
- Keep public imports disabled until a dedicated hardened execution environment is validated.
- To roll back application code, restore a previously tested checkout, rebuild its sandbox image, and restart the services. Preserve the database backup.

The optional legacy nginx configuration is an alternative reverse proxy example. The retired single-service unit must not be used.
