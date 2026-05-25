# Akash Node Overview

## Introduction

The Akash Network is a decentralized cloud computing marketplace built on the Cosmos SDK and powered by Tendermint (CometBFT) consensus. Running a node on the Akash Network allows you to participate in the network, validate transactions, and contribute to the decentralized infrastructure.

## Chain Details

| Property | Value |
|----------|-------|
| Chain ID | `akashnet-2` |
| Coin Denomination | `uakt` (1 AKT = 1,000,000 uakt) |
| Framework | Cosmos SDK |
| Consensus Engine | Tendermint / CometBFT |
| Binary | `akash` (or `provider-services` for providers) |
| Block Time | ~6 seconds |
| Address Prefix | `akash` |
| Key Algorithm | `secp256k1` |
| Minimum Gas Price | `0.025uakt` |
| GitHub Repository | `akash-network/node` |

## Node Types

### Full Node

A full node stores the complete blockchain state and validates all transactions and blocks. It does not participate in consensus but serves as a reliable data source and relay for the network.

**Use cases:**

- Querying blockchain data without relying on third-party RPC endpoints
- Running an Akash provider that needs reliable chain access
- Supporting network decentralization
- Building applications that interact with the Akash chain
- Serving as a sentry node to protect a validator

### Validator Node

A validator node is a full node that actively participates in the consensus process by proposing and voting on new blocks. Validators must stake AKT tokens and are rewarded for correct behavior but penalized (slashed) for misbehavior.

**Use cases:**

- Earning block rewards and transaction fees
- Participating in governance
- Securing the network through consensus
- Supporting the Akash ecosystem

## Why Run a Node

| Reason | Full Node | Validator |
|--------|-----------|-----------|
| Self-sovereign chain access | Yes | Yes |
| No reliance on third-party RPCs | Yes | Yes |
| Query blockchain data directly | Yes | Yes |
| Earn staking rewards | No | Yes |
| Participate in governance voting | No | Yes |
| Support network security | Indirectly | Directly |
| Required for running a provider | Recommended | Optional |

## Network Architecture

The Akash Network uses a standard Cosmos SDK architecture:

```
                    +-------------------+
                    |   Validators      |
                    |  (Consensus Set)  |
                    +--------+----------+
                             |
                    +--------v----------+
                    |   Sentry Nodes    |
                    | (DDoS Protection) |
                    +--------+----------+
                             |
              +--------------+--------------+
              |              |              |
     +--------v---+  +------v-----+  +-----v------+
     | Full Nodes |  | Full Nodes |  | Full Nodes |
     |  (Public)  |  | (Providers)|  |   (RPC)    |
     +------------+  +------------+  +------------+
```

### Consensus Process

1. A validator is selected as the block proposer based on their voting power (proportional to staked AKT).
2. The proposer creates a new block containing pending transactions.
3. Other validators verify and vote on the block in two rounds (pre-vote and pre-commit).
4. Once two-thirds of validators agree, the block is committed.
5. Validators and their delegators earn rewards proportional to their stake.

### Slashing Conditions

Validators can be penalized for:

| Violation | Penalty | Jail Duration |
|-----------|---------|---------------|
| Double signing | 5% of staked tokens slashed | Permanent (tombstoned) |
| Downtime (missing blocks) | 0.01% of staked tokens slashed | 10 minutes minimum |

### Active Validator Set

The Akash Network maintains an active validator set. Validators outside this set do not participate in consensus and do not earn rewards. The number of active validators is determined by on-chain governance parameters.

## Network Endpoints

For connecting to the Akash mainnet, the following public endpoints are commonly available:

| Service | Description |
|---------|-------------|
| RPC | Tendermint RPC for transaction broadcasting and queries |
| REST (LCD) | Light Client Daemon API for RESTful queries |
| gRPC | gRPC endpoint for programmatic access |
| P2P | Peer-to-peer networking port (default 26656) |

## Software Components

| Component | Purpose |
|-----------|---------|
| `akash` | The main node binary for running full nodes and validators |
| `cosmovisor` | Process manager for handling chain upgrades automatically |
| `tmkms` | Tendermint Key Management System for secure validator key handling |

## Getting Started

- To run a **full node**, see [Full Node Requirements](./full-node/requirements.md) and [Installation Guide](./full-node/installation.md).
- To become a **validator**, first set up a full node, then follow [Becoming a Validator](./validator/becoming-validator.md).
- For **validator security** best practices, see [Validator Security](./validator/security.md).
- For ongoing **validator operations**, see [Validator Operations](./validator/operations.md).
