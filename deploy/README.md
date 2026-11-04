# Deploy on Vultr

1. Use an existing Vultr Cloud Compute Linux VM or provision a dedicated one. Set up Python 3.10+, Docker, nginx, an HTTPS domain and a certificate. Restrict inbound access to HTTPS and SSH from your admin network.
2. Clone the repository to `/opt/versionbridge`. Build the sandbox with `sudo docker build -t versionbridge-sandbox:1 -f Sandbox.Dockerfile .`. Create a dedicated `versionbridge` system user and group. The service needs Docker access, which is privileged on the VM.
3. Copy `deploy/versionbridge.env.example` to `/etc/versionbridge.env`, owned by root with permissions `0600`. Set the inference key on the VM and use a model listed for your account in the Vultr Console. Set the sandbox location to the actual VM region. Keep public imports disabled on the public demo until you have validated a hardened runtime such as gVisor and reviewed the untrusted project threat model.
4. Install `deploy/versionbridge.service` in `/etc/systemd/system`. Run `sudo systemctl daemon-reload` and `sudo systemctl enable --now versionbridge`. Check `journalctl -u versionbridge` and `curl http://127.0.0.1:8787/api/config`.
5. Adapt `deploy/nginx.conf.example` to your domain and certificate, run `sudo nginx -t`, and reload nginx. Verify the public URL, run a repair and confirm the evidence names your configured Vultr model. Run the containment lab on the same public URL and capture the blocked actions, timeout and cleanup.

Vultr account access, the inference subscription, an SSH target, and a public domain are environment-specific. The deployment files are templates.
