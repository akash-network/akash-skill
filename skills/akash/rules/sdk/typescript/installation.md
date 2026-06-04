# TypeScript SDK Installation

Install and wire up `@akashnetwork/chain-sdk` — the current Akash TypeScript SDK.

> The older `@akashnetwork/akashjs` is deprecated and is not used by the Akash team or these docs. If you find AkashJS in your code, migrate to `chain-sdk`.

## Package

```bash
npm install @akashnetwork/chain-sdk@alpha
# or
yarn add @akashnetwork/chain-sdk@alpha
# or
pnpm add @akashnetwork/chain-sdk@alpha
```

The package is currently published under the `@alpha` dist-tag. The `latest` tag points at an older alpha — **don't install without specifying `@alpha`**, and pin an exact version once you've chosen one (avoid `^` / `~` ranges).

## Requirements

- **Node:** `>=22.14.0 <25`
- **TypeScript:** 5.x (the package ships its own type declarations)
- **Module type:** Dual ESM/CJS — works in both `"type": "module"` and CommonJS projects

## Subpaths

The package exposes three subpaths:

| Subpath | Use |
|---|---|
| `@akashnetwork/chain-sdk` | Default — Node / server entry, gRPC over HTTP/2 |
| `@akashnetwork/chain-sdk/web` | Browser entry, gRPC-Gateway over HTTPS |
| `@akashnetwork/chain-sdk/private-types/<package>` | Raw generated proto types — e.g. `private-types/akash.v1beta4` for `MsgCreateDeployment`, `Source`, `DeploymentID`. Marked `private` because the wire format is generated and may evolve. |

## Top-level exports

From the default entry:

```typescript
import {
  // SDK factories
  createChainNodeSDK,
  createStargateClient,
  createProviderSDK,

  // Tx batching
  transaction,
  msg,

  // Provider auth
  JwtTokenManager,    // AEP-64 JWTs (preferred)
  certificateManager, // mTLS (legacy)

  // SDL
  generateManifest,
  generateManifestVersion,
  yaml,               // tagged template

  // Errors
  SDKError,
  TxError,
} from "@akashnetwork/chain-sdk";
```

From the web entry:

```typescript
import {
  createChainNodeWebSDK,
  createProviderSDK,
  // ... same auth/SDL/error exports
} from "@akashnetwork/chain-sdk/web";
```

Raw proto types when you need them:

```typescript
import {
  MsgCreateDeployment,
  Source,
  DeploymentID,
} from "@akashnetwork/chain-sdk/private-types/akash.v1beta4";

import { MsgCreateLease } from "@akashnetwork/chain-sdk/private-types/akash.v1beta5";
import { MsgCreateCertificate } from "@akashnetwork/chain-sdk/private-types/akash.v1";
```

## Minimal Node setup

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

// Use the SDK
const deployments = await sdk.akash.deployment.v1beta4.getDeployments({
  pagination: { limit: 10 },
});
console.log(deployments);
```

## Minimal web setup (Keplr)

The web entry expects you to supply a `TxClient` (an object with a `signAndBroadcast` method) — typically wired to a browser wallet extension.

```typescript
import { createChainNodeWebSDK } from "@akashnetwork/chain-sdk/web";
import { SigningStargateClient } from "@cosmjs/stargate";

const offlineSigner = window.keplr.getOfflineSigner("akashnet-2");
const stargate = await SigningStargateClient.connectWithSigner(
  "https://rpc.akashnet.net:443",
  offlineSigner,
);

const sdk = createChainNodeWebSDK({
  query: { baseUrl: "https://api.akashnet.net" }, // gRPC-Gateway
  tx:    { signer: stargate },
});
```

## Transport retries

Retries are off by default. To enable on queries (never on tx):

```typescript
const sdk = createChainNodeSDK({
  query: { baseUrl: "https://akash-grpc.publicnode.com:443" },
  tx:    { signer },
  transportOptions: {
    retry: { maxAttempts: 3, maxDelayMs: 2000 },
  },
});
```

Retries only fire on gRPC codes `Unavailable`, `DeadlineExceeded`, `Internal`, `Unknown`. Use [`cockatiel`](https://www.npmjs.com/package/cockatiel) under the hood.

## Troubleshooting

### Wrong tag installed

```bash
npm ls @akashnetwork/chain-sdk
# If you see 1.0.0-alpha.0 (old), reinstall:
npm install @akashnetwork/chain-sdk@alpha
```

### Node version error

```
Engines incompatibility: requires node >=22.14.0 <25
```

Upgrade Node, or use `nvm use 22`.

### CJS / ESM interop

If you're in a CJS project requiring an ESM-only build:

```javascript
// CommonJS — use the require export
const { createChainNodeSDK } = require("@akashnetwork/chain-sdk");
```

The dual-build package.json `exports` map handles both.

### `private-types/*` not resolving

You're probably on the old `1.0.0-alpha.0` — the subpath map changed in the `@alpha` channel. Reinstall.

## See also

- **@chain-node-sdk.md** — Node-side flows: create deployment, list bids, accept lease, batch txs
- **@chain-web-sdk.md** — Browser flows with wallet extensions
- **@provider-sdk.md** — Provider client and the JWT-auth pattern for direct provider calls
