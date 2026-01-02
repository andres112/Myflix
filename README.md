# MyFlix – Self‑Hosted Jellyfin on K3s (Phases 0–7)

> **Status:** Complete through Phase 7 (Full‑Strict TLS). All commands are inline and reproducible.  
> **Anonymization:** Domains, IPs, usernames, and IDs are placeholders.

---

## Overview

MyFlix is a personal media‑streaming stack on a single‑node **K3s** cluster. It runs **Jellyfin** (with Intel VAAPI), fronted by **Traefik** and exposed via **Cloudflare Tunnel**. TLS is end‑to‑end using a **Cloudflare Origin Certificate**. No router ports are opened.

---

## Phase 0 – Hardware & OS Setup

### Host
- **Machine:** Intel i5‑7200U (4 threads), 8 GiB RAM, Intel HD 620 (VAAPI)
- **OS:** Ubuntu 24.04 Desktop
- **Hostname/User/IP:** `<your-hostname>` / `<your-user>` / `<your-server-ip>`
- **Security:** SSH key‑only + 2‑factor PAM + UFW + Fail2Ban

### Folders
```bash
sudo mkdir -p /srv/jellyfin/{config,cache,fonts} /srv/media
sudo chown -R <your-user>:<your-user> /srv/jellyfin /srv/media
```

### Base packages
```bash
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y curl ufw fail2ban intel-media-va-driver-non-free
sudo ufw allow from 192.168.0.0/16
sudo ufw enable
```

---

## Phase 1 – Install K3s

```bash
curl -sfL https://get.k3s.io | sh -s - --disable traefik --disable servicelb
# REQUIRED AFTER REBOOT SERVER.
sudo chmod 644 /etc/rancher/k3s/k3s.yaml
mkdir -p ~/.kube && sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config && sudo chown $USER:$USER ~/.kube/config
kubectl get nodes -o wide
```

If networking fails (e.g., `dial tcp 10.43.0.1:443: i/o timeout`), reinstall K3s to restore the default **Flannel** CNI.

---

## Phase 2 – Helm & Namespaces

```bash
curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
kubectl create namespace traefik
kubectl create namespace myflix
```

**Project structure** on your workstation:
```
myflix/
├─ charts/
│  ├─ cloudflare/
│  │   ├─ Chart.yaml
│  │   ├─ values.yaml
│  │   └─ templates/
│  │       ├─ _helpers.tpl
│  │       ├─ configmap.yaml
│  │       ├─ deployment.yaml
│  │       ├─ secret.yaml
│  │       └─ serviceaccount.yaml
│  ├─ jellyfin/
│  │   ├─ Chart.yaml
│  │   ├─ values.private.yaml
│  │   ├─ values.yaml
│  │   └─ templates/
│  │       ├─ _helpers.tpl
│  │       ├─ deployment.yaml
│  │       ├─ ingressroute.yaml
│  │       ├─ NOTES.txt
│  │       ├─ pv-pvc.yaml
│  │       ├─ service.yaml
│  │       └─ backup/
│  │           ├─ configmap-script.yaml
│  │           ├─ cronjob.yaml
│  │           ├─ role.yaml
│  │           ├─ rolebinding.yaml
│  │           └─ serviceaccount.yaml
│  └─ traefik-sec/
│      ├─ Chart.yaml
│      ├─ values.yaml
│      └─ templates/
│          ├─ _helpers.tpl
│          ├─ middleware.yaml
│          ├─ NOTES.txt
└─ README.md
```

Copy to the server:
```bash
scp -r ~/projects/myflix <your-user>@<your-server-ip>:~/myflix
```

---

## Phase 3 – Deploy Traefik (Helm)

Add chart and install to the **traefik** namespace with NodePorts and CRD provider options.

```bash
helm repo add traefik https://traefik.github.io/charts
helm repo update

helm upgrade --install traefik traefik/traefik   --namespace traefik   --create-namespace   --set service.type=NodePort   --set ports.web.nodePort=30080   --set ports.websecure.nodePort=30443   --set ingressClass.enabled=true   --set ingressClass.isDefaultClass=true   --set providers.kubernetesCRD.allowCrossNamespace=true   --set logs.general.level=INFO
```

**Verify**
```bash
kubectl -n traefik get pods,svc
kubectl -n traefik logs deploy/traefik | tail -n 50
```

**Access locally**: `http://<your-server-ip>:30080` and `https://<your-server-ip>:30443`.

> Temporary dashboard access (optional & insecure): add `--set ports.traefik.expose.enabled=true` during testing; remove for production.

---

## Phase 4 – Deploy Jellyfin (Helm, VAAPI)

From your cloned repo on the host:
```bash
cd ~/myflix/charts/jellyfin
helm upgrade --install jellyfin .   -n myflix -f values.yaml -f values.private.yaml   --atomic --wait --timeout 5m --history-max 5
```

**Expected mounts**
```
/srv/jellyfin/config  -> /config
/srv/jellyfin/cache   -> /cache
/srv/media            -> /media
/dev/dri/renderD128   -> VAAPI device
```

**Local test (through Traefik web entrypoint)**  
Open: `http://<your-server-ip>:30080` → Jellyfin setup wizard.  
CLI check:
```bash
kubectl -n myflix get pods,svc,ingress
curl -v -H "Host: <your-jellyfin-local-domain>" http://<your-server-ip>:30080
```

---

## Phase 5 – Validation & Troubleshooting

| Issue | Symptom | Resolution |
|---|---|---|
| CNI/Networking broken | `i/o timeout` to `10.43.0.1:443` | Reinstall/repair K3s to restore Flannel |
| 404 via Traefik | No route | Ensure `providers.kubernetesIngress.enabled=true` or use IngressRoute (Phase 7) |
| Host header mismatch | Browser adds port | Use `curl -H "Host: jellyfin.local.lan"` |
| Missing middleware | `"secure-headers" does not exist` | Don’t reference until created (Phase 7 `traefik-sec`) |

Cluster healthy when `kubectl get pods -A` shows **Running**.

---

## Phase 6 – Cloudflare Tunnel (Zero Ports Exposed)

Create tunnel and route a hostname (placeholder values used).

### One-time on workstation
```bash
cloudflared tunnel login
cloudflared tunnel create myflix-tunnel
cloudflared tunnel route dns myflix-tunnel <subdomain>.<your-domain>
# Copy the credentials JSON (<tunnel-id>.json) to your server, e.g. /tmp/<tunnel-id>.json
```

### Kubernetes secrets & Helm deploy
```bash
kubectl -n myflix create secret generic cloudflared-credentials   --from-file=credentials.json=/tmp/<tunnel-id>.json

cd ~/myflix/charts/cloudflare
helm upgrade --install cloudflare .   --namespace myflix   --atomic --wait --timeout 5m --history-max 5
```

**Verify QUIC + hostname**
```bash
kubectl -n myflix logs deploy/cloudflare | egrep "Registered tunnel|Serving tunnel|protocol=quic" | tail -n 20
```

> Initially you can block public traffic with a Cloudflare WAF rule until TLS is hardened in Phase 7.

---

## Phase 7 – Full‑Strict TLS + Security Hardening

**Goal:** Cloudflare Edge → (HTTPS) → Traefik → Jellyfin with **Origin Cert** and Traefik **IngressRoute** + secure headers.

### 7.1 Origin certificate
Issue an **Origin Certificate** in Cloudflare for `<subdomain>.<your-domain>` and create a TLS secret:
```bash
kubectl -n myflix create secret tls tls-origin-cert   --cert=/tmp/origin.crt --key=/tmp/origin.key
```

### 7.2 Security middleware (Helm chart: `traefik-sec`)
```bash
cd ~/myflix/charts/traefik-sec
# First pass (setupMode=true) to relax during wizard or testing, then tighten.
helm upgrade --install traefik-sec .   --namespace traefik   --set setupMode=true   --atomic --wait --timeout 5m --history-max 5

# Tighten headers (HSTS, CSP, no framing, nosniff, etc.)
helm upgrade traefik-sec .   --namespace traefik   --set setupMode=false   --atomic --wait --timeout 5m --history-max 5
```

### 7.3 IngressRoute for Jellyfin (replace Ingress)
Example `spec` (this is what the chart renders):
```yaml
spec:
  entryPoints:
    - websecure
  routes:
    - match: Host(`<subdomain>.<your-domain>`)
      kind: Rule
      services:
        - name: jellyfin-svc
          port: 8096
      middlewares:
        - name: traefik-sec-headers
          namespace: traefik
  tls:
    secretName: tls-origin-cert
```

### 7.4 Point tunnel to Traefik HTTPS
Ensure the Cloudflare tunnel forwards to Traefik **HTTPS** with the correct SNI/Host:
```yaml
# In the cloudflared ConfigMap (values), conceptually:
ingress:
  - hostname: <subdomain>.<your-domain>
    service: https://traefik.traefik.svc.cluster.local:443
    originRequest:
      originServerName: <subdomain>.<your-domain>
      httpHostHeader: <subdomain>.<your-domain>
  - service: http_status:404
```

**Roll the tunnel after changes**
```bash
helm upgrade cloudflare . -n myflix --atomic --wait
kubectl -n myflix rollout status deploy/cloudflare
```

### 7.5 Verify end‑to‑end
```bash
curl -IL https://<subdomain>.<your-domain> --ssl-no-revoke
openssl s_client -connect <subdomain>.<your-domain>:443 -servername <subdomain>.<your-domain> </dev/null 2>/dev/null | openssl x509 -noout -subject -issuer -dates
kubectl -n traefik logs deploy/traefik | grep <subdomain>.<your-domain> | tail -n 20
```

Expected: `302 → 200 OK` from Jellyfin; HSTS/CSP headers present; valid Edge→Origin chain.

---

## Phase 8 – Backup Strategy (Cloud‑Only, Free Tier)

**Goal:** Back up **only** Jellyfin configuration + database (the `config` folder) off‑site using **Cloudflare R2** free tier.  
**Exclusions:** media and cache (not backed up).  
**Schedule:** every **2 days** at **03:00 Europe/Zurich**.  
**Retention:** keep the **last 5** backups; prune older ones.

### 8.1 Prerequisites (Cloudflare R2)
1. Create an R2 bucket, e.g. **`myflix-backups`**.  
2. Create an **R2 Access Key** (Account API Token) with **Admin Read & Write**.  
   - Security tip: consider a **dedicated Cloudflare account** exclusively for MyFlix backups to scope impact.  
3. Note your **Account ID** and **R2 endpoint**:  
   `https://<CF_ACCOUNT_ID>.r2.cloudflarestorage.com`

### 8.2 Kubernetes Secret (store keys only; never commit)
```bash
kubectl create ns myflix 2>/dev/null || true
kubectl -n myflix create secret generic rclone-r2-secret   --from-literal=AWS_ACCESS_KEY_ID='<ACCESS_KEY_ID>'   --from-literal=AWS_SECRET_ACCESS_KEY='<SECRET_ACCESS_KEY>'
```

**Outcome:** Off‑site, free‑tier automated backups of Jellyfin config+DB, with retention and Zurich‑time scheduling.  
**Security:** Account ID may be public; keys live only in K8s Secret; nothing sensitive committed to Git.

---

## Uninstall / Reset (optional helpers)

```bash
# Jellyfin
helm -n myflix uninstall jellyfin

# Traefik security middleware
helm -n traefik uninstall traefik-sec

# Cloudflare tunnel
helm -n myflix uninstall cloudflare
kubectl -n myflix delete secret cloudflared-credentials

# Traefik
helm -n traefik uninstall traefik
```

---

## Current State (after Phase 7)

- ✅ K3s single‑node healthy (Flannel CNI)
- ✅ Traefik in `traefik` namespace
- ✅ Jellyfin running with VAAPI
- ✅ Cloudflare Tunnel active (QUIC)
- ✅ Full‑Strict TLS via Origin Certificate
- ✅ Security headers enforced (HSTS, CSP, frame‑deny, nosniff)
- ✅ No router ports exposed

---

## Next Phases (preview)

8) **GitOps** with ArgoCD or Flux (Helm‑native, dashboards, SSO, protected access)  
9) **Backups**: config only (no media), retention policy, free/backblaze‑style tiers (e.g., Cloudflare R2)  
10) **Observability**: Prometheus + Loki + Grafana, long‑term logs, alerting

---

## Credits & Acknowledgments

- **Jellyfin** – Open‑source media server — https://jellyfin.org  
- **K3s** – Lightweight Kubernetes by SUSE/Rancher — https://k3s.io  
- **Traefik** – Ingress controller / modern proxy — https://traefik.io  
- **Helm** – Kubernetes package manager — https://helm.sh  
- **Cloudflare Tunnel (cloudflared)** — https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/  
- **Ubuntu Linux** — https://ubuntu.com

© 2025 Home Media Server Project
