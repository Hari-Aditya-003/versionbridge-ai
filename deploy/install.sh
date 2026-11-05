#!/usr/bin/env bash
# Run from a reviewed checkout on a dedicated Ubuntu 24.04 development VM.
set -euo pipefail
if [[ ${EUID} -ne 0 || $# -ne 1 ]]; then
    echo "Usage: sudo bash deploy/install.sh PUBLIC_HOSTNAME" >&2
    exit 2
fi
domain=$1
if [[ ! $domain =~ ^[A-Za-z0-9][A-Za-z0-9.-]{0,200}$ ]]; then
    echo "Invalid public hostname" >&2
    exit 2
fi
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends docker.io caddy python3 ca-certificates
systemctl enable --now docker
getent group versionbridge >/dev/null || groupadd --system versionbridge
id versionbridge-web >/dev/null 2>&1 || useradd --system --gid versionbridge --no-create-home --shell /usr/sbin/nologin versionbridge-web
id versionbridge-worker >/dev/null 2>&1 || useradd --system --gid versionbridge --no-create-home --shell /usr/sbin/nologin versionbridge-worker
usermod -aG docker versionbridge-worker
install -d -o versionbridge-worker -g versionbridge -m 2770 /var/lib/versionbridge
install -d -o versionbridge-worker -g versionbridge -m 700 /var/lib/versionbridge/workspaces
docker build -t versionbridge-sandbox:1 -f Sandbox.Dockerfile .
if [[ ! -f /etc/versionbridge-web.env ]]; then
    cat > /etc/versionbridge-web.env <<'ENV'
HOST=127.0.0.1
PORT=8787
ENABLE_JOB_QUEUE=1
EXTERNAL_WORKER=1
PUBLIC_DEMO=1
VERSIONBRIDGE_DB=/var/lib/versionbridge/runs.sqlite3
ENV
fi
if [[ ! -f /etc/versionbridge-worker.env ]]; then
    cat > /etc/versionbridge-worker.env <<'ENV'
VERSIONBRIDGE_DB=/var/lib/versionbridge/runs.sqlite3
SANDBOX_LOCATION="Vultr Cloud Compute"
TMPDIR=/var/lib/versionbridge/workspaces
INFERENCE_BUDGET_USD=5
INFERENCE_DAILY_REQUESTS=30
INFERENCE_INPUT_USD_PER_MILLION=3
INFERENCE_OUTPUT_USD_PER_MILLION=3
ENV
fi
chown root:root /etc/versionbridge-web.env
chmod 600 /etc/versionbridge-web.env
chown root:root /etc/versionbridge-worker.env
chmod 600 /etc/versionbridge-worker.env
install -m 644 deploy/versionbridge-web.service deploy/versionbridge-worker.service /etc/systemd/system/
cat > /etc/caddy/Caddyfile <<CADDY
$domain {
    encode gzip
    header {
        X-Content-Type-Options nosniff
        Referrer-Policy strict-origin-when-cross-origin
        X-Frame-Options DENY
    }
    request_body {
        max_size 8KB
    }
    reverse_proxy 127.0.0.1:8787 {
        flush_interval -1
    }
}
CADDY
caddy validate --config /etc/caddy/Caddyfile
systemctl daemon-reload
systemctl enable --now versionbridge-worker versionbridge-web caddy
systemctl reload caddy
echo "Deployment started. Check https://$domain/readyz and https://$domain/demo.html"
