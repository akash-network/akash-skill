---
name: akash-node
description: >
  Run an Akash Network full node or validator. Covers hardware and network requirements,
  full-node installation, state sync, becoming a validator, validator operations,
  slashing avoidance, key management (consensus key + operator key), monitoring, and
  sentry node patterns. Use for "Akash validator", "Akash full node", "Akash state sync",
  "Akash validator setup", "Akash sentry node", "Akash slashing", "Akash consensus key",
  "Akash node upgrade".
license: MIT
metadata:
  author: Akash Network
  version: "3.0.0"
  argument-hint: <task-description>
---

# Akash Node & Validator Operations

This skill covers running an Akash full node and (optionally) operating it as a validator: installation, state sync, validator setup, security, and day-to-day operations.

For **deploying workloads** to Akash, use the `akash-network:akash` skill. For **running an Akash provider** (the compute supply side), use `akash-network:akash-provider`.

## Terminology (node/validator perspective)

- **Full node** — a node that holds the full chain state and participates in p2p gossip. Required substrate for both validators and query-serving infrastructure.
- **Validator** — a full node that also participates in consensus (signing blocks). Identified by an **operator address** (`akashvaloper1...`) and a **consensus public key**.
- **Operator key** — the wallet that owns the validator (`akash1...` → `akashvaloper1...`). Used for staking, claiming rewards, editing the validator description.
- **Consensus key** — the key the node uses to sign blocks (ed25519). Stored in `priv_validator_key.json`. Compromise = double-sign risk.
- **Self-bond** — AKT staked by the validator itself, as opposed to delegations.
- **Commission rate** — fraction of delegator rewards the validator keeps.
- **Slashing** — penalty for double-signing (5% of stake, permanent jail) or downtime (0.01%, unjailable). Both burn AKT.
- **Sentry node** — a non-validating full node that fronts your validator on the p2p layer. Hides the validator's IP from DDoS / direct attack.
- **State sync** — fast bootstrap method: download a recent state snapshot rather than replaying every block from genesis.
- **AKT** (`uakt`) — chain token. **What validators care about.** All gas (`--gas-prices`, `minimum-gas-prices`), staking (`create-validator --amount`, `delegate`, `redelegate`, `unbond`), self-bond, slashing, and validator rewards are denominated in `uakt`. `1 AKT = 1,000,000 uakt`.
- **ACT** (`uact`) — deployment-payment token. Used by deployers for SDL pricing and lease payments; validators normally don't touch this directly. Mentioned here only so you don't confuse it with `uakt` when reading deployer-side docs.

For deployer-side terminology, see `akash-network:akash`'s `rules/terminology.md`.

## What this skill covers

### Full node
- **@rules/full-node/requirements.md** — Hardware, network, OS
- **@rules/full-node/installation.md** — `akash` binary install, genesis, config
- **@rules/full-node/state-sync.md** — Bootstrap from a recent snapshot

### Validator
- **@rules/validator/becoming-validator.md** — `create-validator` transaction, initial bond, configuration
- **@rules/validator/operations.md** — Day-to-day: editing description, withdrawing rewards, unjailing, signing
- **@rules/validator/security.md** — Sentry nodes, key management, HSM/KMS, double-sign protection

### Overview
- **@rules/overview.md** — Architecture, when to run a node, choosing the right setup

## Critical rules

- **Never run two validators with the same consensus key.** Double-signing burns 5% of your stake and jails the validator permanently. If you migrate to a new host, securely move the key — don't copy it. Use a tombstone file or hardware KMS.
- **Back up `priv_validator_key.json`.** But also: protect it like a private key. Encrypt at rest, restrict to one user, never log it.
- **Watch your peer count and block height.** A validator that falls more than ~10,000 blocks behind risks downtime jailing. Set up alerts.
- **Sentry node your validator if you accept external delegations.** Direct exposure of the validator's RPC/p2p ports is a DDoS target.
- **Test upgrades on a sandbox network first.** Cosmos chain upgrades occasionally require new binaries with specific migration logic; running the wrong binary can corrupt state.
- **Set `minimum-gas-prices` correctly.** Validators that accept zero-fee transactions get spammed.

## Architectural patterns

### Single full node (querying / development)

```
peers ──► full node ──► RPC clients
```

Simple. No consensus, no validator. Good for query-serving infrastructure or local development.

### Validator with sentries

```
peers ──► sentry 1 ──┐
peers ──► sentry 2 ──┼──► validator (no public p2p)
peers ──► sentry 3 ──┘         │
                              consensus
```

Sentries proxy p2p; the validator only connects to its own sentries. Hides validator IP, reduces attack surface.

### Validator with HSM/KMS

```
validator host ──► tmkms (signing service) ──► HSM / YubiHSM
```

`priv_validator_key.json` is never on disk; signing requests are proxied to a hardware module. Industry standard for high-stake validators.

## Quick reference

```bash
# Install (Linux x86_64)
curl -sSfL https://raw.githubusercontent.com/akash-network/node/main/install.sh | sh

# Initialize a node
akash init <moniker> --chain-id akashnet-2

# Start
akash start

# Check status
akash status

# Validator info
akash query staking validator <akashvaloper1...>

# Stake more
akash tx staking delegate <akashvaloper1...> 1000000uakt \
  --from <key-name> --gas auto --gas-adjustment 1.3

# Unjail (after downtime)
akash tx slashing unjail --from <operator-key>
```

## Companion skills

- **`akash-network:akash`** — Deployer skill. Useful background if you also use deployments on the network you operate.
- **`akash-network:akash-provider`** — Provider operations. Different role, but providers must be able to talk to a full node (their own or another's).

## Additional resources

- [Akash Network Docs — Nodes & Validators](https://akash.network/docs/nodes/)
- [akash-network/node repo](https://github.com/akash-network/node)
- [Cosmos SDK validator guide](https://docs.cosmos.network/main/validators/validator-setup)
- [tmkms](https://github.com/iqlusioninc/tmkms) — signing service
