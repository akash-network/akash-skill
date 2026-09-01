# Deployment Methods Overview

There are four ways to **deploy** to Akash and one way to **consume** managed inference on Akash. **Pick one and commit to it for the conversation** — methods are not interchangeable mid-flow because the auth model, command surface, and wallet semantics all differ.

This page exists because conflating these methods is the most common mistake. The SKILL.md's "Choosing a Deployment Method" section is the canonical decision rule; this page is the longer reference for each option.

## Two questions, in order

**1. Are you *deploying* a workload or *consuming* a hosted model?**

- **Deploying** (you write SDL, you own the runtime, you pay in ACT) → continue to question 2.
- **Consuming** (you call an LLM API, AkashML hosts it, you pay in USD credits) → **AkashML**. Stop here; the wallet/auth questions below don't apply. See [@akashml/overview.md](akashml/overview.md).

**2. (Deployment only) Do you want Console to manage the wallet, or do you want self-custody?**

- **Console-managed wallet** → Console API. You sign up on console.akash.network, generate an API key, and authenticate every request with `x-api-key`. The Console account owns the on-chain wallet, holds the funds, and signs transactions on your behalf. No private keys ever leave Console's infrastructure.
- **Self-custody** → CLI, TypeScript SDK, or Go SDK. You hold the private key (in `~/.akash/keys`, a browser wallet like Keplr, a Ledger, or wherever), and your code signs each transaction locally before broadcasting.

Within the deployment paths there is no "Console API + my own wallet." A Console account IS the wallet — the API key authenticates as that account, period. If a user wants to deploy from a self-custody wallet (Keplr or hardware), they need the CLI or an SDK.

AkashML sits *outside* the deploy/self-custody axis entirely: it is a managed consumption surface, not a wallet model. Bringing it up alongside Console API in a "managed vs self-custody" comparison is a category error — they solve different problems.

## Console has two web UIs — disambiguate

- **Standard Console** (`console.akash.network`) — managed wallet. The Console API in this skill drives this product.
- **Console Air** ([github.com/akash-network/console-air](https://github.com/akash-network/console-air)) — self-custody UI for Keplr or hardware wallets. **Self-hosted** — there is no hosted URL at `console-air.akash.network`; users clone the repo and run it locally. It is a **UI**, not an API. This skill does not cover it; programmatic self-custody users go CLI or SDK.

## The four deployment methods at a glance

| Method | Wallet | Auth | Language surface | When to pick it |
|---|---|---|---|---|
| **Console API** | Managed | `x-api-key` header | HTTP + JSON | CI/CD, server-to-server, integrations, anything where you have a deploy account but no private keys |
| **Akash CLI** | Self-custody | Local key + signature | `provider-services` binary | Shell scripting, manual workflows, full local control |
| **TypeScript SDK** | Self-custody | Wallet adapter (Keplr or mnemonic) | `@akashnetwork/chain-sdk` | dApps, Node.js services, any TS/JS integration |
| **Go SDK** | Self-custody | Local key | Go modules | Backend Go services, custom tooling |

## Consumption — AkashML

Plus one consumption path, served by the same network but on a different problem:

| Surface | Wallet | Auth | Language surface | When to pick it |
|---|---|---|---|---|
| **AkashML** | No wallet — USD credits on AkashML account | `Authorization: Bearer akml-...` | HTTP + JSON (OpenAI- and Anthropic-compatible) | You want to **call** an LLM, not host one. RAG, chat, batch inference, agent backends |

## Console API

REST API at `https://console-api.akash.network/v1`. Authentication is `x-api-key: <key>` (not `Authorization: Bearer` — that header is for JWT-based session auth).

**Strengths**
- Programmatic deployments via simple HTTP
- No certificate management
- No private-key handling
- Deployments funded automatically from account credits, in USD
- Stripe-funded; no need to acquire AKT manually

**Limitations**
- Depends on Console as a service
- Can only spend from the Console account's wallet
- Rate limits apply

See **@console-api/** for full reference.

## Akash CLI

Command-line `provider-services` binary against a self-custody wallet.

**Strengths**
- Full control
- Scriptable
- Works against any RPC node
- No third-party dependency

**Limitations**
- Requires local key management
- Requires acquiring AKT
- More moving parts (keys, mnemonics, fees, gas)

See **@cli/** for installation and command reference.

## TypeScript SDK

`@akashnetwork/chain-sdk` for Node.js and browsers.

**Strengths**
- Native JS/TS integration
- Works with browser wallet adapters (Keplr)
- Type safety
- Self-custody — keys stay client-side

**Limitations**
- More code than curl
- Requires SDK knowledge

See **@sdk/typescript/** for documentation.

## Go SDK

Go modules built on the Cosmos SDK and Akash chain-api.

**Strengths**
- High performance
- Native blockchain integration
- Self-custody

**Limitations**
- Go-only
- More setup than other paths

See **@sdk/go/** for documentation.

## AkashML (consumption path)

REST API at `https://api.akashml.com/v1` (OpenAI-compatible) and `https://api.akashml.com/anthropic` (Anthropic-compatible). Authentication is `Authorization: Bearer <key>`. Keys begin with `akml-`. **Not** an `x-api-key` header — that belongs to Console API on a different host.

**Strengths**
- Drop-in for the OpenAI and Anthropic SDKs (just change `baseURL`)
- No SDL, no wallet, no AKT/ACT, no leases
- USD-credit billing on AkashML account
- Open-source models running on Akash compute

**Limitations**
- Consumption only — you cannot host your own model here
- No on-chain visibility (billing is off-chain USD credits, not `uact`)
- Model catalog is dynamic; pin IDs, not "latest"

See **@akashml/** for full reference.

## Quick start by method

### Console API (your API key)

```bash
curl -X POST https://console-api.akash.network/v1/deployments \
  -H "x-api-key: $AKASH_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "sdl": "version: \"2.0\"\nservices:\n  web:\n    image: nginx:1.25.3\n..."
    }
  }'
```

No `deposit`: Console funds the deployment from the account's credit balance. Response includes `dseq`, the on-chain manifest, and the signed `MsgCreateDeployment` result.

### CLI (self-custody)

```bash
# Install
curl -sfL https://raw.githubusercontent.com/akash-network/provider/main/install.sh | bash
sudo mv ./bin/provider-services /usr/local/bin/

# Create a wallet
provider-services keys add deploy

# Fund it (acquire AKT externally), then create the deployment
provider-services tx deployment create deploy.yaml --from deploy --gas auto --gas-adjustment 1.3

# After bids arrive
provider-services tx market lease create --dseq <dseq> --provider <provider> --from deploy
```

### TypeScript SDK (self-custody)

```typescript
import { SigningStargateClient } from "@cosmjs/stargate";
import { MsgCreateDeployment } from "@akashnetwork/chain-sdk/private-types/akash.v1beta4";

const client = await SigningStargateClient.connectWithSigner(rpcUrl, wallet);
const result = await client.signAndBroadcast(address, [{
  typeUrl: "/akash.deployment.v1beta4.MsgCreateDeployment",
  value: MsgCreateDeployment.fromPartial({ ... }),
}], "auto");
```

### Go SDK (self-custody)

```go
import (
    "pkg.akt.dev/go/node/deployment/v1beta4"
    "github.com/cosmos/cosmos-sdk/client"
)

msg := &v1beta4.MsgCreateDeployment{ ... }
// build, sign, and broadcast with a configured cosmos-sdk client.Context
```

### AkashML (consumption, not deployment)

```bash
curl -X POST https://api.akashml.com/v1/chat/completions \
  -H "Authorization: Bearer $AKASHML_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-ai/DeepSeek-V4-Flash",
    "messages": [{"role": "user", "content": "Hello from AkashML"}]
  }'
```

No SDL is involved. The response is a standard OpenAI chat completion. See **@akashml/quickstart.md** for the end-to-end signup-to-inference walkthrough.

## Switching methods mid-conversation

If the user explicitly says they want to switch ("can we do this via the API instead?"):

1. Acknowledge the switch.
2. Treat any state from the prior method (deployments created on-chain) as still valid — they don't need to be migrated, since the chain doesn't care which client created them.
3. Apply the new method's rules from that point on: new commands, new auth, new examples.

Do **not** silently mix methods. If the user is mid-CLI workflow and you suggest a Console API call, you are violating their chosen path.

## Authentication summary

| Auth mechanism | Console API | CLI | SDK | AkashML |
|---|---|---|---|---|
| `x-api-key` header | ✅ primary | ❌ | ❌ | ❌ |
| `Authorization: Bearer <key>` (API key) | ❌ (Bearer is reserved for JWTs) | ❌ | ❌ | ✅ primary (`akml-...`) |
| Local wallet key | ❌ | ✅ primary | ✅ primary | ❌ |
| Browser wallet adapter (Keplr) | ❌ | ❌ | ✅ (TS SDK in browser) | ❌ |
| `Authorization: Bearer <jwt>` | ✅ (for Console-account JWT session auth) | ❌ | ❌ | ❌ |
| mTLS certificate | ❌ ([deprecated](../cli/mtls-legacy.md) for Console API; CLI direct-to-provider calls still use it where applicable) | ✅ (CLI direct provider calls) | ✅ (SDK direct provider calls) | ❌ |

The collision worth flagging: **`Authorization: Bearer`** means a JWT on the Console API and an API key on AkashML. They are different services on different hosts; don't carry credentials across.
