# Deployment Methods Overview

There are four ways to deploy to Akash. **Pick one and commit to it for the conversation** — methods are not interchangeable mid-flow because the auth model, command surface, and wallet semantics all differ.

This page exists because conflating these methods is the most common mistake. The SKILL.md's "Choosing a Deployment Method" section is the canonical decision rule; this page is the longer reference for each option.

## The one decision that matters

**Do you want Console to manage the wallet, or do you want self-custody?**

- **Console-managed wallet** → Console API. You sign up on console.akash.network, generate an API key, and authenticate every request with `x-api-key`. The Console account owns the on-chain wallet, holds the funds, and signs transactions on your behalf. No private keys ever leave Console's infrastructure.
- **Self-custody** → CLI, TypeScript SDK, or Go SDK. You hold the private key (in `~/.akash/keys`, a browser wallet like Keplr, a Ledger, or wherever), and your code signs each transaction locally before broadcasting.

There is no fifth path. There is no "Console API + my own wallet." A Console account IS the wallet — the API key authenticates as that account, period. If a user wants to deploy from a self-custody wallet (Keplr / Leap / hardware), they need the CLI or an SDK.

## Console has two web UIs — disambiguate

- **Standard Console** (`console.akash.network`) — managed wallet. The Console API in this skill drives this product.
- **Console Air** ([github.com/akash-network/console-air](https://github.com/akash-network/console-air)) — self-custody UI for Keplr / Leap / hardware wallets. **Self-hosted** — there is no hosted URL at `console-air.akash.network`; users clone the repo and run it locally. It is a **UI**, not an API. This skill does not cover it; programmatic self-custody users go CLI or SDK.

## The four methods at a glance

| Method | Wallet | Auth | Language surface | When to pick it |
|---|---|---|---|---|
| **Console API** | Managed | `x-api-key` header | HTTP + JSON | CI/CD, server-to-server, integrations, anything where you have a deploy account but no private keys |
| **Akash CLI** | Self-custody | Local key + signature | `akash` binary | Shell scripting, manual workflows, full local control |
| **TypeScript SDK** | Self-custody | Wallet adapter (Keplr, Leap, mnemonic) | `@akashnetwork/chain-sdk` | dApps, Node.js services, any TS/JS integration |
| **Go SDK** | Self-custody | Local key | Go modules | Backend Go services, custom tooling |

## Console API

REST API at `https://console-api.akash.network/v1`. Authentication is `x-api-key: <key>` (not `Authorization: Bearer` — that header is for JWT-based session auth).

**Strengths**
- Programmatic deployments via simple HTTP
- No certificate management
- No private-key handling
- Deposits expressed in USD (translated server-side)
- Stripe-funded; no need to acquire AKT manually

**Limitations**
- Depends on Console as a service
- Can only spend from the Console account's wallet
- Rate limits apply

See **@console-api/** for full reference.

## Akash CLI

Command-line `akash` binary against a self-custody wallet.

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
- Works with browser wallet adapters (Keplr, Leap)
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

## Quick start by method

### Console API (your API key)

```bash
curl -X POST https://console-api.akash.network/v1/deployments \
  -H "x-api-key: $AKASH_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "sdl": "version: \"2.0\"\nservices:\n  web:\n    image: nginx:1.25.3\n...",
      "deposit": 5
    }
  }'
```

`deposit` is a USD number, not a denom string. Response includes `dseq`, the on-chain manifest, and the signed `MsgCreateDeployment` result.

### CLI (self-custody)

```bash
# Install
curl -sSfL https://get.akash.network/install.sh | sh

# Create a wallet
akash keys add deploy

# Fund it (acquire AKT externally), then create the deployment
akash tx deployment create deploy.yaml --from deploy --gas auto --gas-adjustment 1.3

# After bids arrive
akash tx market lease create --dseq <dseq> --provider <provider> --from deploy
```

### TypeScript SDK (self-custody)

```typescript
import { SigningStargateClient } from "@cosmjs/stargate";
import { MsgCreateDeployment } from "@akashnetwork/akash-api/akash/deployment/v1beta4";

const client = await SigningStargateClient.connectWithSigner(rpcUrl, wallet);
const result = await client.signAndBroadcast(address, [{
  typeUrl: "/akash.deployment.v1beta4.MsgCreateDeployment",
  value: MsgCreateDeployment.fromPartial({ ... }),
}], "auto");
```

### Go SDK (self-custody)

```go
import (
    "github.com/akash-network/node/client"
    "github.com/akash-network/akash-api/go/node/deployment/v1beta4"
)

txClient := client.NewTxClient(ctx, ...)
msg := &v1beta4.MsgCreateDeployment{ ... }
resp, err := txClient.Broadcast(ctx, msg)
```

## Switching methods mid-conversation

If the user explicitly says they want to switch ("can we do this via the API instead?"):

1. Acknowledge the switch.
2. Treat any state from the prior method (deployments created on-chain) as still valid — they don't need to be migrated, since the chain doesn't care which client created them.
3. Apply the new method's rules from that point on: new commands, new auth, new examples.

Do **not** silently mix methods. If the user is mid-CLI workflow and you suggest a Console API call, you are violating their chosen path.

## Authentication summary

| Auth mechanism | Console API | CLI | SDK |
|---|---|---|---|
| `x-api-key` header | ✅ primary | ❌ | ❌ |
| Local wallet key | ❌ | ✅ primary | ✅ primary |
| Browser wallet adapter (Keplr/Leap) | ❌ | ❌ | ✅ (TS SDK in browser) |
| `Authorization: Bearer <jwt>` | ✅ (for Console-account JWT session auth) | ❌ | ❌ |
| mTLS certificate | ❌ ([deprecated](../certificates/mtls-legacy.md) for Console API; CLI direct-to-provider calls still use it where applicable) | ✅ (CLI direct provider calls) | ✅ (SDK direct provider calls) |
