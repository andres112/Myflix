# MyFlix – Self-Hosted Jellyfin on K3s

## Overview

MyFlix is a personal media streaming stack running on a single-node K3s cluster.  
It deploys Jellyfin with GPU acceleration and Traefik as the ingress controller.

### Host

- Ubuntu 24.04 Desktop (hostname and user redacted)
- Static IP (redacted)
- SSH key-only + 2FA
- `/srv/jellyfin/{config,cache}`, `/srv/media` directories created.

### Kubernetes

- K3s single node
- Namespace: `myflix`
- Helm v3 used for deployment

---

## Project Structure

```
myflix/
├─ helmfile.yaml
├─ charts/
│  ├─ traefik/ (fetched from Helm repo)
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

## Setup

### 1. Prepare Host

```bash
curl -fsSL https://get.k3s.io | sh -s -
curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
sudo apt install -y kubectl
```

### 2. Copy Project

```bash
scp -r ~/projects/myflix <your-user>@<your-server-ip>:~/myflix
```

### 3. Deploy

```bash
ssh <your-user>@<your-server-host>
cd ~/myflix
kubectl create namespace myflix
helmfile apply
```

---

## Verify

```bash
kubectl get pods -n myflix
kubectl get svc -n myflix
kubectl get ingress -n myflix
```

Access locally:  
`http://jellyfin.local.lan:8096`

Access remotely (later):  
`https://jellyfin.<your-domain>` via Cloudflare Tunnel

---

## Next Steps

- Phase 6: Cloudflare Tunnel (secure remote access)
- Phase 7: Full-Strict TLS (Cloudflare Origin Cert)
- Add Traefik middlewares: HSTS, CSP, Frame-Options
- Add media auto-backup (Rclone + R2)

---

---

## References & Credits

- [Jellyfin](https://jellyfin.org/) – Open source media system
- [Traefik](https://traefik.io/) – Cloud-native edge router
- [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/) – Secure remote access
- [K3s](https://k3s.io/) – Lightweight Kubernetes
- [Helm](https://helm.sh/) – Kubernetes package manager

---

© 2025 Andrés Dorado – Home Media Server Project
