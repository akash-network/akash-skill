# Akash Provider Overview

An Akash provider is an entity that supplies compute resources to the Akash Network marketplace. Providers run Kubernetes clusters and the Akash provider software to accept deployment orders, bid on workloads, and host tenant applications.

## What Is a Provider?

A provider is the supply side of the Akash marketplace. Providers:

- Register on the Akash blockchain with their capabilities and attributes
- Monitor the chain for deployment orders matching their resources
- Automatically bid on orders via the bid engine
- Deploy and manage tenant workloads on Kubernetes
- Earn ACT (paid in `uact`) for hosting deployments

## Why Become a Provider?

| Benefit | Description |
|---------|-------------|
| Revenue | Earn income from underutilized compute capacity |
| Low Barrier | Any Kubernetes cluster can become a provider |
| Flexible Pricing | Set your own pricing strategy |
| Decentralized | No intermediary takes a cut |
| GPU Monetization | High demand for GPU compute at competitive rates |
| Growing Market | Increasing demand for decentralized cloud |

## Provider Architecture

```
┌─────────────────────────────────────────────────┐
│                 Akash Blockchain                 │
│  (Orders, Bids, Leases, Payments, Attributes)   │
└──────────────────┬──────────────────────────────┘
                   │
                   │  Monitors chain / submits bids
                   │
┌──────────────────▼──────────────────────────────┐
│              Provider Process                    │
│  ┌───────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ Bid Engine│  │ Manifest │  │  Lease       │  │
│  │           │  │ Handler  │  │  Manager     │  │
│  └───────────┘  └──────────┘  └──────────────┘  │
│  ┌───────────────────┐  ┌────────────────────┐  │
│  │ Hostname Operator │  │ Inventory Operator │  │
│  └───────────────────┘  └────────────────────┘  │
└──────────────────┬──────────────────────────────┘
                   │
                   │  Deploys workloads
                   │
┌──────────────────▼──────────────────────────────┐
│              Kubernetes Cluster                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ Pods     │  │ Services │  │  Ingress     │  │
│  │ (Tenant  │  │          │  │  Controller  │  │
│  │ workloads│  │          │  │              │  │
│  └──────────┘  └──────────┘  └──────────────┘  │
│  ┌──────────┐  ┌──────────────────────────────┐ │
│  │ Storage  │  │  GPU (nvidia-device-plugin)  │ │
│  └──────────┘  └──────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

### Key Components

#### Provider Process

The core provider daemon that runs alongside Kubernetes:

- **Bid Engine** - Monitors the blockchain for deployment orders, evaluates whether the provider can fulfill them, calculates a price, and submits bids automatically
- **Manifest Handler** - Receives and validates SDL manifests from tenants after a lease is created
- **Lease Manager** - Tracks active leases, monitors resource usage, handles lease lifecycle events (creation, withdrawal, closure)

#### Hostname Operator

Manages DNS and ingress for tenant workloads:

- Maps random hostnames to tenant services
- Configures ingress rules for HTTP/HTTPS traffic
- Handles custom domain assignments when tenants use dedicated hostnames

#### Inventory Operator

Monitors cluster resources and reports availability:

- Tracks available CPU, memory, storage, and GPU resources
- Reports allocatable capacity to the bid engine
- Ensures the provider does not overcommit resources

#### Kubernetes Cluster

The underlying infrastructure where tenant workloads run:

- Each deployment gets its own Kubernetes namespace
- Pod security policies isolate tenant workloads
- Persistent volumes provide durable storage
- Ingress controller routes external traffic

## Provider Lifecycle

```
1. Set up Kubernetes cluster
2. Install provider software (Helm chart)
3. Configure provider attributes and pricing
4. Register provider on-chain
5. Provider begins monitoring for orders
6. Bid engine submits bids automatically
7. Tenants accept bids, creating leases
8. Provider deploys workloads
9. Provider earns revenue per block
10. Provider withdraws earnings periodically
```

## Provider Registration

Providers register on-chain with:

```bash
provider-services tx provider create provider.yaml --from provider-wallet
```

The registration includes:

| Field | Description |
|-------|-------------|
| `host` | Provider's publicly accessible URI |
| `attributes` | Key-value pairs describing capabilities |
| `info.email` | Contact email |
| `info.website` | Provider website |

Example `provider.yaml`:

```yaml
host: https://provider.example.com:8443
attributes:
  - key: region
    value: us-west
  - key: host
    value: akash
  - key: tier
    value: community
  - key: organization
    value: myorg
info:
  email: provider@example.com
  website: https://example.com
```

## Provider Economics

### Revenue Model

```
Revenue = Sum(lease_price × blocks_active) for all active leases
```

- Providers earn per-block payments from each active lease
- Payments are in `uact` (the standard SDL pricing/lease-payment denom post-Mainnet-17; the chain still lists `uakt` in `min_deposits`/`bid_min_deposits`)
- Providers can withdraw accumulated earnings periodically

### Cost Considerations

| Cost Category | Examples |
|---------------|----------|
| Hardware | Servers, GPUs, storage, networking |
| Bandwidth | Ingress/egress traffic |
| Electricity | Power for compute infrastructure |
| Maintenance | System updates, monitoring, support |
| Staking | AKT required for provider registration |

## Next Steps

- **@requirements.md** - Hardware and software requirements
- **@setup/kubernetes-cluster.md** - Setting up the Kubernetes cluster
- **@setup/provider-installation.md** - Installing provider software
- **@configuration/attributes.md** - Configuring provider attributes
- **@configuration/pricing.md** - Setting up pricing
