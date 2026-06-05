# SDK Overview

Akash provides official SDKs for programmatic integration with the network.

> **Chain message versions** (verify against your installed package — these change with chain upgrades):
> - `akash.deployment.v1beta4.*` — `MsgCreateDeployment`, `MsgUpdateDeployment`, `MsgCloseDeployment`, `MsgDepositDeployment`
> - `akash.market.v1beta5.*` — `MsgCreateBid`, `MsgCreateLease`, `MsgCloseBid`, `MsgCloseLease`
> - `akash.cert.v1.*` — `MsgCreateCertificate`, `MsgRevokeCertificate`
>
> Older code targeting `v1beta3` deployment or `v1beta4` market will fail with a chain-side parse error. When porting examples, double-check the version segment of any `typeUrl` and SDK proxy path.

## TypeScript: `@akashnetwork/chain-sdk`

The current TypeScript SDK. **Do not use the older `@akashnetwork/akashjs`** — it is deprecated and no longer maintained.

- **Package:** [`@akashnetwork/chain-sdk`](https://www.npmjs.com/package/@akashnetwork/chain-sdk)
- **Source:** https://github.com/akash-network/chain-sdk (TypeScript lives under `ts/`)
- **Install:** `npm install @akashnetwork/chain-sdk@alpha` — you must use the `@alpha` tag; the `latest` npm tag points at an older alpha. Pin an exact version (avoid `^` / `~`).
- **Node engine:** `>=22.14.0 <25`.
- **Module type:** Dual ESM/CJS.

**Three entry points:**

| Subpath | Use |
|---|---|
| `@akashnetwork/chain-sdk` | Node / server (gRPC over HTTP/2) |
| `@akashnetwork/chain-sdk/web` | Browser (gRPC-Gateway over HTTPS — for wallet-extension flows) |
| `@akashnetwork/chain-sdk/private-types/*` | Raw generated proto types — e.g. `.../private-types/akash.v1beta4` for `MsgCreateDeployment`, `Source`, `DeploymentID` |

**Top-level exports:**

- `createChainNodeSDK`, `createChainNodeWebSDK` — chain client factories
- `createProviderSDK` — provider client (only `getStatus` / `streamStatus` today)
- `createStargateClient` — signer factory (wraps a mnemonic or `DirectSecp256k1HdWallet`)
- `transaction(sdk, messages, options?)`, `msg(method, data)` — multi-message tx batching
- `JwtTokenManager` — AEP-64 JWT signing for self-custody provider auth
- `certificateManager` — mTLS cert management (legacy; prefer JWT for new code)
- `generateManifest`, `generateManifestVersion`, `yaml` (tagged template), type `SDLInput` — SDL parsing & manifest helpers
- `SDKError`, `TxError` — error classes

Messages are accessed as methods on the SDK proxy at runtime:

```typescript
sdk.akash.deployment.v1beta4.createDeployment({ ... })
sdk.akash.market.v1beta5.createLease({ ... })
sdk.akash.market.v1beta5.getBids({ ... })
sdk.akash.cert.v1.createCertificate({ ... })
```

There is no manual type registry; you don't import `MsgCreateDeployment` directly unless you want raw types from `private-types`.

**What chain-sdk does NOT do** (so you don't go looking for it):
- Provider HTTP helpers like `sendManifest`, `queryLeaseLogs`, `leaseShell` — these were in the old akashjs and were **not ported**. For logs / events / shell, mint a JWT with `JwtTokenManager` and call the provider's HTTPS/WSS endpoints directly via `fetch` / `WebSocket` / `undici`. See **@../deploy/console-api/operations.md** for the URL templates.
- `getAkashTypeRegistry` — gone. `createStargateClient` returns a ready-to-use signer; the SDK proxy handles serialization.
- `getRpc` — gone. Just pass `baseUrl` strings to `createChainNodeSDK` and `createStargateClient`.

## Go: `pkg.akt.dev/go`

The current Go bindings live in a single module, `pkg.akt.dev/go` (repo `akash-network/chain-sdk`, `go/` subdir):

- [`pkg.akt.dev/go`](https://pkg.go.dev/pkg.akt.dev/go) — generated protobuf message types and codecs (`pkg.akt.dev/go/node/deployment/v1beta4`, `pkg.akt.dev/go/node/market/v1beta5`, `pkg.akt.dev/go/node/cert/v1`).

Use the Cosmos SDK (`github.com/cosmos/cosmos-sdk`) for transaction building, signing, and broadcasting.

## SDK Comparison

### TypeScript (`chain-sdk`)

Best for:
- Web applications (use the `/web` entry)
- Node.js services (use the default entry)
- Browser-based dApps with Keplr

Features:
- Chain transactions and queries via a flat proxy
- AEP-64 JWT minting for self-custody (`JwtTokenManager`)
- SDL manifest generation
- mTLS cert helpers (legacy)

### Go SDK

Best for:
- Backend services
- Custom tooling
- High-performance applications
- Provider development

Features:
- Full Cosmos SDK integration
- Direct gRPC access
- Idiomatic protobuf message types
- Provider integration code shared with the provider daemon

## Quick Start — TypeScript

```typescript
import { createChainNodeSDK, createStargateClient } from "@akashnetwork/chain-sdk";

const signer = createStargateClient({
  baseUrl: "https://rpc.akashnet.net:443",
  signerMnemonic: process.env.MNEMONIC!,
});

const sdk = createChainNodeSDK({
  query: { baseUrl: "https://akash-grpc.publicnode.com:443" },
  tx:    { signer },
});

// Query
const deployments = await sdk.akash.deployment.v1beta4.getDeployments({
  pagination: { limit: 10 },
});

// Tx
const result = await sdk.akash.deployment.v1beta4.createDeployment({
  // ... see @typescript/chain-node-sdk.md for full message shape
});
```

## Quick Start — Go

```go
import (
    dv1 "pkg.akt.dev/go/node/deployment/v1"        // DeploymentID lives here, NOT in v1beta4
    "pkg.akt.dev/go/node/deployment/v1beta4"        // MsgCreateDeployment, GroupSpec(s)
    deposit "pkg.akt.dev/go/node/types/deposit/v1"  // Deposit type
    "github.com/cosmos/cosmos-sdk/client"
)

// Prefer the constructor — in v1beta4 the message has fields
// ID / Groups / Hash / Deposit (there is no Version or Depositor field):
//   func NewMsgCreateDeployment(id dv1.DeploymentID, groups []v1beta4.GroupSpec,
//                               hash []byte, dep deposit.Deposit) *v1beta4.MsgCreateDeployment
msg := v1beta4.NewMsgCreateDeployment(
    dv1.DeploymentID{Owner: address, DSeq: dseq}, // owner bech32 + dseq
    groups,       // []v1beta4.GroupSpec
    manifestHash, // []byte — the deployment Hash
    dep,          // deposit.Deposit
)

// broadcast msg using a configured client.Context
// Confirm field/symbol names for your pinned version at
// https://pkg.go.dev/pkg.akt.dev/go/node/deployment/v1beta4
```

## When to use an SDK vs. the Console API

- Use the **TypeScript SDK** when you need self-custody (Keplr or hardware) and want JS/TS code.
- Use the **Go SDK** for self-custody backends.
- Use the **Console API** (not this chapter) if you want HTTP + an API key and don't mind that Console manages the wallet. See **@../deploy/console-api/**.

The SDK paths and the Console API path are not interchangeable — pick one and stay there. See the SKILL.md "Choosing a Deployment Method" section.

## See also

- **@typescript/installation.md** — Install `chain-sdk` and wire it up
- **@typescript/chain-node-sdk.md** — Node-side flows (full deploy + bids + leases)
- **@typescript/chain-web-sdk.md** — Browser flows with wallet adapters
- **@typescript/provider-sdk.md** — Provider client + JWT auth + raw provider HTTPS calls
- **@go/installation.md** — Install Go modules
- **@go/client-setup.md** — Configure cosmos client + akash-api
- **@../deploy/console-api/operations.md** — For provider URL templates referenced by the SDK examples
