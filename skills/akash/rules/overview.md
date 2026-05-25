# Akash Network Overview

Akash Network is a decentralized cloud computing marketplace that connects users who need compute resources with providers who have underutilized capacity.

## How It Works

```
┌─────────────┐     1. Create SDL      ┌─────────────┐
│   Tenant    │ ───────────────────►   │   Akash     │
│  (Deployer) │                        │  Blockchain │
└─────────────┘                        └─────────────┘
      │                                      │
      │  4. Accept Bid                       │ 2. Broadcast Order
      │     Send Manifest                    │
      ▼                                      ▼
┌─────────────┐     3. Submit Bid      ┌─────────────┐
│  Provider   │ ◄───────────────────   │  Provider   │
│  (Selected) │                        │   Network   │
└─────────────┘                        └─────────────┘
      │
      │  5. Deploy Containers
      ▼
┌─────────────┐
│  Kubernetes │
│   Cluster   │
└─────────────┘
```

### Deployment Flow

1. **Create SDL** - Tenant writes a Stack Definition Language (SDL) file describing their workload
2. **Create Deployment** - Tenant broadcasts deployment order to the blockchain
3. **Bidding** - Providers submit bids for the deployment
4. **Accept Bid** - Tenant accepts a bid, creating a lease
5. **Send Manifest** - Tenant sends the SDL manifest to the provider
6. **Deploy** - Provider deploys containers on their Kubernetes cluster

## Key Components

### Blockchain (akash-node)

The Akash blockchain handles:
- Deployment orders and leases
- Payment escrow and settlement
- Provider registration and auditing
- Governance and staking

### Providers

Providers run Kubernetes clusters and the Akash provider software to:
- Monitor for deployment orders
- Submit bids based on pricing rules
- Deploy and manage workloads
- Report lease status

### Console

[Akash Console](https://console.akash.network) is a web interface for:
- Creating deployments without CLI
- Managing leases and providers
- Viewing deployment logs and status

### Console API

The [Console API](https://console-api.akash.network/v1/swagger) provides REST endpoints for:
- Programmatic deployments
- Managed wallet operations
- SDL validation

## Network Details

| Property | Value |
|----------|-------|
| Chain ID | `akashnet-2` |
| Chain Token | AKT — denom `uakt` (1 AKT = 1,000,000 uakt). Used for gas, staking, validator rewards. |
| Deployment Token | ACT — denom `uact` (1 ACT = 1,000,000 uact). Used for SDL pricing, bid prices (the rate providers offer), deployment escrow/deposit, and lease payments. **Separate from AKT.** Provider-side bid *deposit* (`bidMinDeposit`, the `deposit` field on `MsgCreateBid`) is in `uakt`, not `uact` — it's anti-spam collateral, not a compute payment. |
| Self-custody deployers | Must mint ACT by burning AKT before depositing to a deployment. Console API users skip this (Console funds the managed wallet with ACT directly). |
| Block Time | ~6 seconds |
| Consensus | Tendermint BFT |

## Payment Model

- **Escrow-based** - Funds deposited upfront
- **Per-block billing** - Charged every ~6 seconds
- **Native ACT** - SDL pricing and lease payments in `uact` (ACT's micro-denomination, minted by burning AKT)
- **Refundable** - Unused escrow returned on close

## Architecture Layers

### Application Layer
- SDL files define workloads
- Docker containers run applications
- Kubernetes manages orchestration

### Protocol Layer
- Deployment marketplace on-chain
- Bid/lease management
- Payment settlement

### Network Layer
- Cosmos SDK blockchain
- IBC for cross-chain assets
- Tendermint consensus

## Comparison with Traditional Cloud

| Aspect | Traditional Cloud | Akash Network |
|--------|------------------|---------------|
| Pricing | Fixed rates | Competitive bidding |
| Payment | Monthly billing | Per-block escrow |
| Providers | Single vendor | Multiple providers |
| Lock-in | Vendor-specific | Portable SDL |
| Control | Provider managed | User controlled |
| Cost | Market rates | Up to 85% lower |

## Use Cases

- **Web Applications** - Deploy any containerized web app
- **AI/ML Workloads** - Access GPU compute at competitive rates
- **Development/Testing** - Spin up ephemeral environments
- **Blockchain Nodes** - Run validator and full nodes
- **Game Servers** - Deploy with dedicated IPs
- **Batch Processing** - Run compute-intensive jobs
