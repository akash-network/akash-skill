# Akash Network Terminology

Key terms and concepts used throughout the Akash Network.

## Deployment Identifiers

### DSEQ (Deployment Sequence)

A unique identifier for a deployment on the Akash blockchain.

```
dseq: 12345678
```

- Assigned when deployment is created on-chain
- Used to reference the deployment in all operations
- Immutable once assigned

### GSEQ (Group Sequence)

Identifies a group within a deployment. Most deployments have a single group (gseq: 1).

```
gseq: 1
```

- Groups allow deploying to multiple providers
- Each group can have different placement requirements
- Starts at 1 for each deployment

### OSEQ (Order Sequence)

Identifies an order within a group. Increments when a lease is closed and reopened.

```
oseq: 1
```

- Starts at 1 for new deployments
- Increments on lease migration or restart
- Used with dseq and gseq to identify a specific lease

### Lease ID

The combination of owner address, dseq, gseq, oseq, and provider address.

```
owner/dseq/gseq/oseq/provider
akash1abc.../12345678/1/1/akash1xyz...
```

## Core Concepts

### SDL (Stack Definition Language)

YAML configuration file defining a deployment:

```yaml
version: "2.0"
services:
  web:
    image: nginx:1.25.3
    expose:
      - port: 80
        to:
          - global: true
profiles:
  compute:
    web:
      resources:
        cpu:
          units: 0.5
        memory:
          size: 512Mi
        storage:
          size: 1Gi
  placement:
    dcloud:
      pricing:
        web:
          denom: uact
          amount: 1000
deployment:
  web:
    dcloud:
      profile: web
      count: 1
```

### Manifest

The SDL converted to a format sent to the provider. Contains deployment instructions without pricing information.

### Deployment

An on-chain record representing a tenant's intent to deploy workloads. Contains:
- Owner address
- SDL hash
- Escrow balance
- State (open, closed)

### Order

A request for bids on a deployment group. Providers monitor for orders matching their capabilities.

### Bid

A provider's offer to fulfill an order at a specific price.

### Lease

A binding agreement between tenant and provider:
- Created when bid is accepted
- Defines price per block
- Allows provider to deploy workload
- Continues until closed or funds depleted

## Actors

### Tenant (Deployer)

The user deploying workloads:
- Creates deployments
- Deposits escrow
- Accepts bids
- Manages leases

### Provider

Entity running compute infrastructure:
- Operates Kubernetes cluster
- Runs provider software
- Submits bids on orders
- Deploys and manages workloads

### Auditor

Trusted entity that verifies provider attributes:
- Signs provider attestations
- Enables attribute filtering
- Builds trust in provider claims

### Validator

Secures the Akash blockchain:
- Runs consensus node
- Validates transactions
- Earns staking rewards

## Payment Terms

### Two tokens — AKT vs ACT

Akash has two separate tokens. Don't conflate them.

| Token | Denom | Purpose |
|---|---|---|
| **AKT** | `uakt` | Chain token — gas, staking, validator rewards. `1 AKT = 1,000,000 uakt`. |
| **ACT** | `uact` | Deployment-payment token — SDL pricing, bid *prices*, deployment escrow/deposit, lease payments. `1 ACT = 1,000,000 uact`. The provider-side bid *deposit* (`MsgCreateBid.deposit`, the anti-spam collateral) defaults to `uakt` — the provider posts 500000 uakt (0.5 AKT) from its balance; `uact` only via a rare burn-mint fallback. |

Self-custody deployers must mint ACT by burning AKT before depositing to a deployment. Console API users skip this — Console funds the managed wallet with ACT directly.

### uact

Micro-ACT, the smallest denomination of the deployment-payment token:

```
1 ACT = 1,000,000 uact
```

### Escrow

Funds deposited for a deployment:
- Required before deployment starts
- Drawn down per block
- Returned on close (minus spent)

### Bid Price

Amount provider charges per block:

```yaml
pricing:
  web:
    denom: uact
    amount: 1000  # per block (~6 seconds)
```

Monthly cost is roughly `amount × blocks_per_month` (a block is ~6 seconds, so on the order of hundreds of thousands of blocks per month). These figures are illustrative only — do not treat them as a quote. For real costs, rely on live price discovery (the bids returned for your deployment) and the pricing in current awesome-akash templates.

## Provider Terms

### Attributes

Key-value pairs describing provider capabilities:

```yaml
attributes:
  region: us-west
  host: akash
  tier: community
```

### Signed By

Auditor signatures that verify provider attributes:

```yaml
signedBy:
  anyOf:
    - akash1auditor...
```

### Bid Engine

Provider component that:
- Monitors for matching orders
- Calculates bid prices
- Submits bids automatically

## Infrastructure Terms

### Kubernetes

Container orchestration platform used by providers:
- Runs workloads as pods
- Manages networking and storage
- Provides service discovery

### Ingress

Kubernetes component exposing services:
- Routes external traffic
- Handles TLS termination
- Provides hostnames for deployments

### Persistent Volume

Storage that survives container restarts:
- Mounted to containers
- Backed by provider storage class
- beta2, beta3, or ram classes

## State Machine

### Deployment States

```
Active: Deployment is running
Closed: Deployment is terminated
```

### Order States

```
Open: Accepting bids
Matched: Bid accepted, lease created
Closed: No longer accepting bids
```

### Lease States

```
Active: Workload running
Reclaiming: Provider has started resource reclamation (AEP-82); deadline = block_time + reclamation window
Closed: Lease terminated
Insufficient Funds: Escrow depleted
```

`Reclaiming` and the paused-group state below only appear on v2.1.0+ leases; pre-2.1
leases never enter them.

### Group States

```
Open: Group active, orders may be created
Paused: Group has no active lease and will not auto-create new orders (e.g. after a reclamation window expires); resume with MsgStartGroup
```

## Resource Reclamation (AEP-82)

**Resource Reclamation** is the v2.1.0 protocol mechanism by which a **provider**
reclaims the resources of an *active* lease after a tenant-declared grace window. It
is distinct from the provider-side Kubernetes cleanup that runs *after* a lease
closes (see the akash-provider skill's "Resource Cleanup on Lease Close").

| Term | Meaning |
|------|---------|
| `MsgLeaseStartReclaim` | Provider-signed message that starts reclamation on an `Active` lease, moving it to `Reclaiming`. Carries `{ id: LeaseID, reason: LeaseClosedReason }`. |
| Reclamation deadline | `block_time + reclamation window`. The provider may close the lease **only after** this deadline; closing before it is rejected. |
| `MsgStartGroup` | Resumes a **paused** group, creating new orders (which inherit the deployment's reclamation requirement). |
| `MsgCloseLease` | Closes a **single lease**. Tenant-initiated close auto-re-orders (the new order inherits the reclamation requirement). |
| `MsgCloseDeployment` | Closes the **whole deployment**; this escrow-level close bypasses the reclamation window. |

See [deploy/cli/deployment-lifecycle.md](deploy/cli/deployment-lifecycle.md) for the
full flow and [sdl/reclamation.md](sdl/reclamation.md) for the SDL field.

## Common Abbreviations

| Abbreviation | Meaning |
|--------------|---------|
| SDL | Stack Definition Language |
| AKT | Akash Token |
| IBC | Inter-Blockchain Communication |
| RPC | Remote Procedure Call |
| gRPC | Google Remote Procedure Call |
| API | Application Programming Interface |
| CLI | Command Line Interface |
| JWT | JSON Web Token |
| mTLS | Mutual TLS |
