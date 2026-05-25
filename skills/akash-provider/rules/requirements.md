# Provider Requirements

Hardware, software, and networking requirements for running an Akash provider.

## Hardware Requirements

### Minimum Specifications

| Component | Minimum | Notes |
|-----------|---------|-------|
| CPU | 4 cores (x86_64) | For provider process + system overhead |
| RAM | 8 GB | Excludes tenant workload memory |
| System Disk | 100 GB SSD | OS, Kubernetes, provider software |
| Tenant Storage | 500 GB SSD | Ephemeral and persistent volumes |
| Network | 100 Mbps | Symmetric upload/download |
| Public IP | 1 static IPv4 | For ingress and provider API |

### Recommended Specifications

| Component | Recommended | Notes |
|-----------|-------------|-------|
| CPU | 32+ cores (x86_64) | More cores = more tenant capacity |
| RAM | 128+ GB | Allows larger tenant workloads |
| System Disk | 500 GB NVMe | Fast storage for Kubernetes |
| Tenant Storage | 2+ TB NVMe | Persistent volume capacity |
| Network | 1 Gbps+ | Higher bandwidth for more tenants |
| Public IPs | Multiple static IPv4 | For IP lease support |

### GPU Provider Requirements

For GPU workloads, add the following:

| Component | Requirement | Notes |
|-----------|-------------|-------|
| GPU | NVIDIA (Kepler or newer) | Must support CUDA |
| GPU Driver | NVIDIA 525+ | Latest stable recommended |
| CUDA | 12.0+ | Matches driver version |
| GPU RAM | Depends on model | See GPU models reference |

Commonly provided GPU models:

| Model | VRAM | Typical Use |
|-------|------|-------------|
| T4 | 16 GB | Inference |
| RTX 3090 | 24 GB | Training, inference |
| A10 | 24 GB | Inference, training |
| A100 | 40/80 GB | Large model training |
| H100 | 80 GB | Large-scale training |

## Software Requirements

### Operating System

| OS | Version | Status |
|----|---------|--------|
| Ubuntu | 22.04 LTS | Recommended |
| Ubuntu | 20.04 LTS | Supported |
| Debian | 11/12 | Supported |
| CentOS/RHEL | 8/9 | Supported |

### Kubernetes

| Component | Version | Notes |
|-----------|---------|-------|
| Kubernetes | 1.27+ | 1.29+ recommended |
| kubectl | Matching K8s version | CLI access required |
| Helm | 3.12+ | For provider chart installation |

### Container Runtime

| Runtime | Version | Notes |
|---------|---------|-------|
| containerd | 1.6+ | Recommended for most setups |
| NVIDIA Container Toolkit | Latest | Required for GPU providers |

### Networking Software

| Component | Purpose |
|-----------|---------|
| nginx-ingress-controller | Routes HTTP/HTTPS traffic to tenant workloads |
| cert-manager (optional) | Automated TLS certificate management |

## Networking Requirements

### Required Ports

| Port | Protocol | Direction | Purpose |
|------|----------|-----------|---------|
| 8443 | TCP | Inbound | Provider API (gRPC/REST) |
| 80 | TCP | Inbound | HTTP ingress for tenant workloads |
| 443 | TCP | Inbound | HTTPS ingress for tenant workloads |
| 6443 | TCP | Inbound | Kubernetes API (internal) |
| 30000-32767 | TCP/UDP | Inbound | NodePort services |
| 26656 | TCP | Outbound | Akash node P2P (if running local node) |
| 26657 | TCP | Outbound | Akash node RPC |

### DNS Requirements

Configure the following DNS records:

| Record | Type | Value | Purpose |
|--------|------|-------|---------|
| `provider.example.com` | A | Provider public IP | Provider API endpoint |
| `*.ingress.example.com` | A/CNAME | Provider public IP | Wildcard for tenant workloads |

Example DNS configuration:

```
provider.example.com.        A    203.0.113.10
*.ingress.example.com.       A    203.0.113.10
```

### Firewall Rules

```bash
# Provider API
ufw allow 8443/tcp

# HTTP/HTTPS ingress
ufw allow 80/tcp
ufw allow 443/tcp

# Kubernetes NodePort range
ufw allow 30000:32767/tcp
ufw allow 30000:32767/udp
```

## Blockchain Requirements

### Akash Node Access

Providers need access to an Akash RPC node:

| Option | Description |
|--------|-------------|
| Public RPC | Use a public endpoint (simplest) |
| Dedicated RPC | Run your own node (recommended for production) |
| Third-party | Use a node service provider |

Public RPC endpoints:

```
https://rpc.akashnet.net:443
https://akash-rpc.polkachu.com:443
https://rpc-akash.ecostake.com:443
```

### Provider Wallet

| Requirement | Details |
|-------------|---------|
| AKT Balance | Minimum 5 AKT for registration transaction |
| Ongoing AKT | Small amount for periodic withdrawal transactions |
| Key Storage | Secure keyring (OS or file backend) |

### Provider Certificate

A valid mTLS certificate is required for provider-tenant communication:

```bash
# Create provider certificate
akash tx cert create server provider.example.com --from provider-wallet

# Verify certificate
akash query cert list --owner $(akash keys show provider-wallet -a)
```

## Storage Requirements

### Storage Classes

Providers should configure at least one storage class:

| Class | Backend | Description |
|-------|---------|-------------|
| `beta2` | SSD/NVMe | Standard persistent storage |
| `beta3` | HDD | Bulk persistent storage |
| `ram` | tmpfs | RAM-backed ephemeral storage |

### Persistent Volume Provisioner

A dynamic volume provisioner is required:

| Provisioner | Use Case |
|-------------|----------|
| local-path-provisioner | Single-node clusters |
| OpenEBS | Multi-node, production |
| Rook-Ceph | Multi-node, distributed |
| Longhorn | Multi-node, lightweight |

## Resource Planning

### Capacity Estimation

Reserve resources for system overhead:

```
Allocatable CPU    = Total CPU    - 2 cores (system)
Allocatable Memory = Total Memory - 4 GB (system)
Allocatable GPU    = Total GPU    - 0 (all allocatable)
```

### Example Provider Configurations

#### Small Provider (Entry Level)

| Resource | Specification |
|----------|---------------|
| CPU | 8 cores |
| RAM | 32 GB |
| Storage | 500 GB NVMe |
| GPU | None |
| Network | 500 Mbps |
| Capacity | ~5-10 small deployments |

#### Medium Provider

| Resource | Specification |
|----------|---------------|
| CPU | 64 cores |
| RAM | 256 GB |
| Storage | 4 TB NVMe |
| GPU | 2x RTX 3090 |
| Network | 1 Gbps |
| Capacity | ~20-50 deployments |

#### Large Provider

| Resource | Specification |
|----------|---------------|
| CPU | 256+ cores |
| RAM | 1 TB+ |
| Storage | 20+ TB NVMe |
| GPU | 8x A100 80GB |
| Network | 10 Gbps |
| Capacity | ~100+ deployments |

## Pre-Flight Checklist

Before setting up your provider, verify:

- [ ] Server meets minimum hardware requirements
- [ ] Supported operating system installed
- [ ] Public static IP address available
- [ ] Required ports open in firewall
- [ ] DNS records configured (A record + wildcard)
- [ ] Akash RPC endpoint accessible
- [ ] Provider wallet funded with AKT
- [ ] NVIDIA drivers installed (GPU providers only)

## Next Steps

- **@setup/kubernetes-cluster.md** - Set up Kubernetes
- **@setup/provider-installation.md** - Install provider software
- **@setup/configuration.md** - Initial provider configuration
