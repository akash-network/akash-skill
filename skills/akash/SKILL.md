---
name: akash
description: >
  Build, validate, and deploy workloads to the Akash Network — the decentralized cloud
  marketplace. Covers SDL syntax & examples, choosing a deployment method (Console API,
  CLI, TypeScript/Go SDKs), authentication (API key, JWT, self-custody wallets),
  deployment lifecycle, fetching logs/events via the provider proxy, and fee grants/authz.
  Use for "deploy to Akash", "Akash SDL", "Akash Console API", "Akash CLI deploy",
  "Akash API key", "x-api-key", "Akash deploy logs", "stream Akash logs", "integrate
  Akash into my app", "@akashnetwork/chain-sdk", "@akashnetwork".
license: MIT
metadata:
  author: Akash Network
  version: "3.0.0"
  argument-hint: <task-description>
---

# Akash — Deploy Workloads

This skill covers everything needed to deploy and operate a workload on the Akash Network: writing SDL, picking a deployment method, authenticating, creating the deployment, accepting bids, and reading logs/events from the live deployment.

For running an Akash **provider**, use the `akash-network:akash-provider` skill. For running a **full node or validator**, use `akash-network:akash-node`.

## Critical Rules

**NEVER use `:latest` or omit image tags.** Always specify explicit version tags so deployments are reproducible.

```yaml
# CORRECT
image: nginx:1.25.3
image: postgres:16

# WRONG
image: nginx:latest
image: nginx          # implies :latest
```

**Native denom is `uact`, not `uakt`.** The token denom was renamed; any older docs you find referencing `uakt` are stale.

## Choosing a Deployment Method

This is the most important decision in this skill — and the one most easily gotten wrong. When the user asks to deploy and hasn't specified the method, **ask once which path they want, then commit to it for the rest of the conversation.** Do not silently switch methods. If the user explicitly asks to switch later, do so cleanly and stay on the new path.

There are **four** paths:

| # | Method | Wallet model | Auth | When to use |
|---|---|---|---|---|
| 1 | **Console API** | Managed (Console account owns the wallet) | `x-api-key` header | CI/CD, server-to-server, any backend that wants HTTP + an API key. No private-key handling. |
| 2 | **Akash CLI** | Self-custody (you hold the keys) | Local key + signature | Shell scripting, manual workflows, full control. |
| 3 | **TypeScript SDK** | Self-custody (browser wallet, hardware, or local key) | SDK signs locally | dApps, Node.js services, anywhere you want JS/TS code to deploy. |
| 4 | **Go SDK** | Self-custody | SDK signs locally | Backend Go services, custom tooling. |

### The concept that bites everyone

**A Console account *is* a wallet.** When you sign up on `console.akash.network` and generate an API key, that API key authenticates as your Console account — and your account has a managed wallet underneath it. Deployments spend from that wallet. There is no separate "Console API + bring your own wallet" mode.

If a user has a self-custody wallet (Keplr or Ledger) and wants to deploy from *that* wallet, they need the **CLI** or **an SDK**. The Console API will not sign with an external wallet.

### Console has two flavors — disambiguate

- **Standard Console** at `console.akash.network` — managed wallet. This is what the Console API in this skill operates on.
- **Console Air** ([github.com/akash-network/console-air](https://github.com/akash-network/console-air)) — self-custody UI for Keplr or hardware wallets. **Self-hosted** — there is no official hosted URL at `console-air.akash.network`; users clone the repo and run it locally or on their own infrastructure. **Out of scope for this skill** (it is a UI, not an API). If a user wants a UI with self-custody, point them at the repo and stop; programmatic self-custody users go CLI or SDK.

### Recognize strong cues — skip the question when they are clear

| If the user mentions… | Commit to… |
|---|---|
| `"I have an API key"`, `"$AKASH_API_KEY"`, `"x-api-key"`, `"curl"`, `"CI/CD"` | Console API |
| `"Keplr"`, `"Ledger"`, `"hardware wallet"`, `"my wallet"`, `"self-custody"`, `"akash keys add"` | CLI or SDK (ask which) |
| `"React app"`, `"Next.js"`, `"@akashnetwork/chain-sdk"` | TypeScript SDK |
| `"Go service"`, `"golang"`, `"cosmos-sdk Go"` | Go SDK |
| `"Console Air"`, `"web UI for my Keplr wallet"` | Console Air (out-of-scope; point to docs) |

If the user is silent on the method, ask. Phrase it as a short menu, not an open-ended question.

### When on the Console API path — ask which language

Once the user commits to Console API, **ask which language** the integration will be written in before producing code. Don't default to curl + Bash unless the user has clearly indicated they want shell — e.g. `"curl"`, `"bash"`, `"shell script"`, `"$AKASH_API_KEY"` in a `.sh` context, or `"CI/CD"` for a generic step. Otherwise the answer should match the runtime they're actually targeting.

Recognize cues; otherwise ask:

| Cue | Language to use |
|---|---|
| `"curl"`, `"bash"`, `"shell"`, `"GitHub Actions"` step | curl + Bash |
| `"Node"`, `"Next.js"`, `"Express"`, `package.json`, `.ts` file | TypeScript / Node `fetch` |
| `"Python"`, `requirements.txt`, `.py` file, `"FastAPI"`, `"Django"` | Python `requests` or `httpx` |
| `"Go"`, `go.mod`, `.go` file | Go `net/http` |
| `"Rust"`, `Cargo.toml` | Rust `reqwest` |

If the user is silent on the language, ask: *"What's your integration written in? I can give you curl, Node/TS, Python, or Go — same flow, different syntax."* Then commit.

This is a separate gate from the deployment-method selection — they happen in sequence. Method first, language second. Once both are chosen, **stay on both** for the rest of the conversation.

### Once committed, stay there

- On the **Console API** path: don't suggest `akash keys add`, don't suggest mTLS certs (deprecated for Console API — see `rules/deploy/certificates/mtls-legacy.md`), don't suggest `akash query market bid list` — every read is an HTTP call with `x-api-key` in whatever language the user picked.
- On the **CLI** path: don't suggest `/v1/deployments` HTTP calls. Don't suggest API keys. Stay on `akash tx ...` / `akash query ...`.
- On the **SDK** paths: don't reach for curl examples or CLI commands; the user wants code.

If the user asks to **switch** ("can we do this via the API instead?"), acknowledge the switch, and from that point on apply the new path's rules.

## Quick Reference

### SDL Structure

Every SDL has four required sections (plus optional `endpoints` for IP leases):

```yaml
version: "2.0"  # or "2.1" for IP endpoints

services:       # Container definitions
profiles:       # Compute resources & placement
deployment:     # Service-to-profile mapping
```

### Minimal SDL Template

```yaml
version: "2.0"

services:
  web:
    image: nginx:1.25.3
    expose:
      - port: 80
        as: 80
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

## Documentation Structure

### Core Concepts
- **@rules/overview.md** — Akash Network introduction and architecture
- **@rules/terminology.md** — Key terms (lease, bid, dseq, gseq, oseq)
- **@rules/pricing.md** — Payment with uact, USDC, IBC denoms

### SDL Configuration
- **@rules/sdl/schema-overview.md** — Version requirements and SDL structure
- **@rules/sdl/services.md** — Service configuration (image, expose, env, credentials)
- **@rules/sdl/compute-resources.md** — CPU, memory, storage, and GPU specifications
- **@rules/sdl/placement-pricing.md** — Provider selection and pricing (uact/USDC)
- **@rules/sdl/deployment.md** — Service-to-profile mapping
- **@rules/sdl/endpoints.md** — IP endpoint configuration (v2.1)
- **@rules/sdl/validation-rules.md** — All constraints and validation rules

### SDL Examples
- **@rules/sdl/examples/web-app.md** — Simple web deployment
- **@rules/sdl/examples/wordpress-db.md** — Multi-service with persistent storage
- **@rules/sdl/examples/gpu-workload.md** — GPU deployment with NVIDIA
- **@rules/sdl/examples/ip-lease.md** — IP endpoint configuration

### Deployment Methods
- **@rules/deploy/overview.md** — Method selection (start here)
- **@rules/deploy/console-api/** — Console API (API key path)
  - `overview.md` — base URL, auth, response shape
  - `authentication.md` — API key (`x-api-key`), JWT minting, API Keys CRUD
  - `deployment-endpoints.md` — full curated endpoint reference
  - `api-key-quickstart.md` — linear walkthrough from "I have an API key" to a running deployment
  - `account-and-funding.md` — Console account, balances, Stripe funding, `/v1/tx`
  - `operations.md` — JWT + provider proxy + logs/events/status/shell
- **@rules/deploy/cli/** — Akash CLI (self-custody path)
- **@rules/deploy/certificates/** — Auth methods; mTLS deprecated for Console API

### SDK Documentation
- **@rules/sdk/overview.md** — SDK comparison and selection
- **@rules/sdk/typescript/** — TypeScript SDK for web and Node.js
- **@rules/sdk/go/** — Go SDK for backend services

### AuthZ (Delegated Permissions)
- **@rules/authz/** — Fee grants and deployment authorization

### Bid Matching (deployer-facing)
- **@rules/bid-matching/overview.md** — When to use, how to run the matcher, how to present results
- **@rules/bid-matching/adaptation-rules.md** — Priority order for SDL changes
- **@rules/bid-matching/matching-rules.md** — SDL ↔ provider field mapping

For live bid-failure diagnosis against the actual provider set, use the standalone `akash-bid-matcher` skill — it is the companion to this one.

### Reference
- **@rules/reference/storage-classes.md** — beta2, beta3, ram storage
- **@rules/reference/gpu-models.md** — Supported NVIDIA GPUs
- **@rules/reference/ibc-denoms.md** — Payment denominations
- **@rules/reference/rpc-endpoints.md** — Public RPC endpoints

## Common Patterns

### Environment Variables
```yaml
services:
  app:
    env:
      - "DATABASE_URL=postgres://..."
      - "NODE_ENV=production"
```

### Persistent Storage
```yaml
profiles:
  compute:
    app:
      resources:
        storage:
          - size: 10Gi
            attributes:
              persistent: true
              class: beta2
```

### GPU Workloads
```yaml
profiles:
  compute:
    ml:
      resources:
        gpu:
          units: 1
          attributes:
            vendor:
              nvidia:
                - model: a100
```

### Payment Options
- **uact** — Native Akash Token (e.g., `amount: 1000`). The CLI / SDK denom.
- **USDC** — via IBC denom (e.g., `denom: ibc/170C677610AC31DF0904FFE09CD3B5C657492170E7E52372E48756B71E56F2F1`).
- Note: the Console API expresses deposits as a **USD number**, not a denom string — translation happens server-side.

## Additional Resources

- **[awesome-akash](https://github.com/akash-network/awesome-akash)** — 100+ production-ready SDL templates
- **[Akash Network Docs](https://akash.network/docs/)** — Official documentation
- **[Console (managed wallet)](https://console.akash.network)** — Web UI; managed-wallet equivalent of this skill's Console API path
- **[Console Air (self-custody, self-hosted)](https://github.com/akash-network/console-air)** — Web UI for Keplr or hardware wallets; clone and run locally
- **[Console API Swagger](https://console-api.akash.network/v1/doc)** — Full OpenAPI spec (this skill curates the deployment-management subset; the full spec also contains Console-UI internals like Stripe, alerts, user signup)
- **[@akashnetwork/chain-sdk](https://www.npmjs.com/package/@akashnetwork/chain-sdk)** — TypeScript SDK (self-custody JWT signing, chain messages)
