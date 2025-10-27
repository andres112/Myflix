# MyFlix – Self-Hosted Jellyfin on K3s

## Overview

MyFlix is a personal media-streaming stack running on a hardened single-node K3s cluster.  
It deploys Jellyfin with Intel VAAPI GPU acceleration and uses Traefik as ingress.  
Networking and security are configured for both local and future Cloudflare-tunneled access.

---

## Host Environment

- **OS:** Ubuntu 24.04 Desktop
- **Hostname:** `<your-hostname>`, user `<your-user>`
- **Static IP:** `<your-server-ip>`
- **Security:** SSH key-only, 2-factor PAM, UFW + Fail2Ban
- **Storage:**
  ```
  /srv/jellyfin/config
  /srv/jellyfin/cache
  /srv/media
  ```
- **GPU:** Intel HD Graphics 620 → `/dev/dri/{card1,renderD128}`
- **CPU/RAM:** i5-7200U (4 threads) / 8 GiB

---

## Kubernetes

- **Distribution:** K3s v1.33.5+k3s1
- **CNI:** Flannel (default)
- **Namespace:** `myflix`
- **Ingress Controller:** Traefik v3 (Helm)
- **Package Manager:** Helm v3

---

## Project Structure

```
myflix/
├─ charts/
│  ├─ traefik/       (installed from upstream repo)
│  ├─ cloudflare/
│  │   ├─ Chart.yaml
│  │   ├─ values.yaml
│  │   └─ templates/
│  │       ├─ deployment.yaml
│  │       ├─ configmap.yaml
│  │       ├─ secret.yaml
│  │       ├─ serviceaccount.yaml
│  │       └─ _helpers.tpl
│  └─ jellyfin/
│      ├─ Chart.yaml
│      ├─ values.yaml
│      └─ templates/
│          ├─ deployment.yaml
│          ├─ service.yaml
│          ├─ ingress.yaml
│          ├─ pv-pvc.yaml
│          └─ _helpers.tpl
```

---

## Installation

### 1. Prepare Host

```bash
sudo apt update && sudo apt full-upgrade -y
curl -sfL https://get.k3s.io | sh -s - --disable traefik --disable servicelb
curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

### 2. Verify Cluster

```bash
sudo chmod 644 /etc/rancher/k3s/k3s.yaml
mkdir -p ~/.kube && sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config && sudo chown $USER:$USER ~/.kube/config
kubectl get nodes && kubectl get pods -A
```

### 3. Copy Project Files

```bash
scp -r ~/projects/myflix <your-user>@<your-server-ip>:~/myflix
# Replace <your-user> and <your-server-ip> with your actual SSH username and server IP or hostname
```

### 4. Install Traefik

```bash
helm repo add traefik https://traefik.github.io/charts
helm repo update
helm install traefik traefik/traefik   -n kube-system   --set service.type=NodePort   --set providers.kubernetesIngress.enabled=true   --set ingressClass.enabled=true   --set ingressClass.isDefaultClass=true
```

### 5. Deploy Jellyfin

```bash
kubectl create namespace myflix
cd ~/myflix/charts/jellyfin
helm upgrade --install jellyfin .   --namespace myflix   --atomic --wait --timeout 5m --history-max 5
```

---

## Verification

```bash
kubectl get pods -n myflix
kubectl get svc -n myflix
kubectl get ingress -n myflix
```

Then from a LAN machine:

```bash
curl -v -H "Host: <your-jellyfin-local-domain>" http://<your-server-ip>:<Traefik-NodePort>
# Replace <your-jellyfin-local-domain> and <your-server-ip> with your actual values
```

Expected response:

```
HTTP/1.1 302 Found
Location: web/
Server: Kestrel
```

→ Jellyfin is online.

---

## Troubleshooting Chronicle

| Issue                                                 | Symptom                                               | Resolution                                                           |
| ----------------------------------------------------- | ----------------------------------------------------- | -------------------------------------------------------------------- |
| **Pods couldn’t reach API (Traefik i/o timeout)**     | `dial tcp 10.43.0.1:443: i/o timeout` in Traefik logs | K3s installed without CNI; reinstalled with default Flannel          |
| **Local-path-provisioner & metrics-server CrashLoop** | Same network failure                                  | Fixed by restoring Flannel networking                                |
| **Ingress 404**                                       | Traefik reachable but no route                        | `providers.kubernetesIngress.enabled=true` added during Helm install |
| **Host header mismatch**                              | Browser adds port → 404                               | Used `curl -H "Host: jellyfin.local.lan"` or iptables redirect       |
| **Missing middleware warning**                        | `"secure-headers@kubernetescrd" does not exist`       | Removed annotation until middleware is defined later                 |
| **Dashboard port config error**                       | Helm schema changed                                   | Correct syntax: `--set ports.traefik.expose.enabled=true` etc.       |
| **Permission denied on kubeconfig**                   | `open /etc/rancher/k3s/k3s.yaml: permission denied`   | Copied file to `~/.kube/config` with `chmod 644`                     |

All components now start cleanly; `kubectl get pods -A` shows all **Running**.

---

## Current State (Phase 5 complete)

- ✅ K3s single-node cluster operational
- ✅ Flannel CNI and service networking functional
- ✅ Traefik ingress routing Jellyfin
- ✅ Jellyfin container running, GPU VAAPI ready
- ✅ Local access via `http://<your-jellyfin-local-domain>:<NodePort>`

---

## Next Phases

1. **Phase 6 – Cloudflare Tunnel:** deploy `cloudflared` pod to expose Jellyfin securely without opening router ports.
2. **Phase 7 – Full-Strict TLS:** use Cloudflare Origin Certificates and Traefik middleware (HSTS, CSP, Frame-Options).
3. **Phase 8 – Media backup:** automate with Rclone + Cloudflare R2.

---

## References

- [Jellyfin Docs](https://jellyfin.org/docs/general/installation/container/)
- [Traefik Helm Chart](https://artifacthub.io/packages/helm/traefik/traefik)
- [K3s Docs](https://docs.k3s.io/)
- [Cloudflare Tunnel Guide](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)

---

© 2025 Home Media Server Project


---

## Phase 6 – Cloudflare Tunnel (Zero Ports Exposed)

Cloudflare Tunnel allows external access to Jellyfin without opening any router ports.  
The tunnel is deployed as a Helm‑managed pod using the `charts/cloudflare` chart.

### Configuration Summary

| Step | Description | Result |
|------|--------------|---------|
| 1 | Created Cloudflare account and registered domain `<your-domain>` | ✅ |
| 2 | Installed `cloudflared` CLI on Windows workstation | ✅ |
| 3 | Authenticated and created tunnel `myflix-tunnel`; noted Tunnel ID | ✅ |
| 4 | Created DNS record via `cloudflared tunnel route dns myflix-tunnel cine.goldenflix.win` | ✅ CNAME auto‑added in Cloudflare |
| 5 | Generated `tunnel.json` and `config.cloudflared.yaml`; uploaded to Ubuntu host | ✅ |
| 6 | Created Kubernetes Secret and ConfigMap for these files | ✅ |
| 7 | Built Helm chart (`charts/cloudflare`) with Deployment + ServiceAccount | ✅ |
| 8 | Set `service: http://traefik.kube-system.svc.cluster.local:80` in ConfigMap | ✅ |
| 9 | Verified tunnel logs – connected via QUIC to Cloudflare regions (ZRH, AMS) | ✅ |
| 10 | Updated Jellyfin Ingress hosts (`jellyfin.local.lan`, `cine.goldenflix.win`) | ✅ |
| 11 | Access through browser at `https://cine.goldenflix.win` confirmed | ✅ |
| 12 | Applied Cloudflare WAF rule to temporarily block public traffic | ✅ |

---

### Helm Installation for Cloudflare Tunnel

```bash
# Pre-create secret from credential JSON (uploaded from workstation)
kubectl -n myflix create secret generic cloudflared-credentials \
  --from-file=credentials.json=/tmp/<your-tunnel-id>.json

# Deploy using Helm
cd ~/myflix/charts/cloudflare
helm upgrade --install cloudflare . -n myflix --atomic --wait
```

Verify deployment:

```bash
kubectl -n myflix get pods -l app.kubernetes.io/name=cloudflare
kubectl -n myflix logs deploy/cloudflare | tail -n 20
```

Expected logs include lines like:

```
Registered tunnel connection … protocol=quic
Serving tunnel on hostname cine.goldenflix.win
```

---

### Troubleshooting Notes (Phase 6)

| Issue | Symptom | Resolution |
|-------|----------|-------------|
| Wrong Traefik namespace | `lookup traefik.traefik.svc.cluster.local: no such host` | Corrected ConfigMap to `kube-system` namespace |
| ConfigMap cache | Pod still used old host reference after Helm upgrade | Forced rollout restart to refresh mount |
| DNS debugging limitations | `cloudflared` image has no shell tools | Deployed temporary BusyBox pod to run `nslookup` |
| Security exposure | Public access visible before TLS hardening | Blocked via Cloudflare WAF and later Access policy |

---

### Security & Operations

- Tunnel remains **locally managed** (YAML/Helm) — not migrated to Cloudflare Zero Trust UI.  
- All outbound only; no open ports on router.  
- Cloudflare WAF temporarily blocks `cine.goldenflix.win` until Phase 7 TLS hardening.  
- QUIC connections verified; latency ≈ 50 ms edge‑to‑origin.  

---

### Verification Commands

```bash
curl -vL https://cine.goldenflix.win --ssl-no-revoke
kubectl -n myflix logs deploy/cloudflare | grep originService
```

Expected result: `404 Not Found` or `302 Found` from Traefik → tunnel and ingress functional.

---

### Current State (Phase 6 Complete)

- ✅ Cloudflare Tunnel deployed and stable  
- ✅ Traefik reachable internally through tunnel  
- ✅ Jellyfin accessible through Cloudflare edge domain  
- ✅ Public access temporarily blocked via WAF  
- ✅ Ready for Phase 7 – Full‑Strict TLS and Security Middlewares

---

