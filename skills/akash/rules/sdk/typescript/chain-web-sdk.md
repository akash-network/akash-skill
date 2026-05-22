# Chain SDK — Browser

Using `@akashnetwork/chain-sdk/web` from a browser application, signing transactions with a wallet extension (Keplr).

If you haven't installed yet, see **@installation.md**.

## Why a separate entry?

The default `chain-sdk` entry uses gRPC over HTTP/2 via `@connectrpc/connect-node`, which doesn't work in browsers. The `/web` entry uses gRPC-Gateway (regular HTTPS) and works wherever `fetch` is available — browsers, Workers, edge runtimes.

```typescript
// Node
import { createChainNodeSDK } from "@akashnetwork/chain-sdk";

// Browser / edge
import { createChainNodeWebSDK } from "@akashnetwork/chain-sdk/web";
```

## Wallet integration (Keplr)

```typescript
import { createChainNodeWebSDK } from "@akashnetwork/chain-sdk/web";
import { SigningStargateClient } from "@cosmjs/stargate";

// Wait for Keplr to be injected
async function getKeplrSigner() {
  if (!window.keplr) throw new Error("Keplr not installed");
  await window.keplr.enable("akashnet-2");
  return window.keplr.getOfflineSigner("akashnet-2");
}

const offlineSigner = await getKeplrSigner();
const accounts = await offlineSigner.getAccounts();
const address = accounts[0].address;

const stargate = await SigningStargateClient.connectWithSigner(
  "https://rpc.akashnet.net:443",
  offlineSigner,
);

const sdk = createChainNodeWebSDK({
  query: { baseUrl: "https://api.akashnet.net" }, // gRPC-Gateway base
  tx:    { signer: stargate },
});
```

## Wallet integration (WalletConnect / hardware)

WalletConnect's offline-signer adapter and Ledger's `LedgerSigner` from `@cosmjs/ledger-amino` both work in the same shape — they expose `signDirect` / `signAmino` and `getAccounts`. Wire them into `SigningStargateClient.connectWithSigner` and the rest of the flow is unchanged.

## Create a deployment from the browser

Same proxy paths as the Node example — but the user approves each tx in their wallet popup.

```typescript
import { generateManifest, generateManifestVersion } from "@akashnetwork/chain-sdk/web";

const sdlText = document.getElementById("sdl").value;
const manifest = generateManifest(sdlText);
const version = generateManifestVersion(manifest);

const dseq = BigInt(Math.floor(Date.now() / 1000));

const result = await sdk.akash.deployment.v1beta4.createDeployment({
  id: { owner: address, dseq },
  groups: manifest.groups,
  version,
  deposit: { denom: "uact", amount: "5000000" },
  depositor: address,
});

// User approved the popup; tx is broadcast.
```

## Querying from the browser

Pure-query usage doesn't need a signer:

```typescript
const sdkQuery = createChainNodeWebSDK({
  query: { baseUrl: "https://api.akashnet.net" },
});

const providers = await sdkQuery.akash.provider.v1beta4.providers({});
```

## Provider proxy considerations

The browser **cannot** call providers directly for logs/events because the provider's TLS cert is pinned to its on-chain wallet address, not signed by a public CA. Browsers will reject the connection.

Workarounds:
1. **Run your own provider-proxy** — the Console monorepo's `apps/provider-proxy/` is a Node service that does identity-pinned cert validation and forwards requests. Host it on infrastructure you control.
2. **Use Console's public provider-proxy** — if one is published in your Console deployment configuration. Hostname is environment-specific; don't hardcode.

For SSR / Node code embedded in a Next.js app, you can avoid the proxy entirely by calling the provider from a server route with the chain-sdk's auth helpers. See **@provider-sdk.md**.

## Bundle considerations

`chain-sdk/web` and its `@cosmjs/*` dependencies are large (~300+ KB minified+gzipped combined). For client-only bundles, tree-shake aggressively:

```typescript
// Good — import only what you need
import { createChainNodeWebSDK, generateManifest } from "@akashnetwork/chain-sdk/web";

// Avoid — pulls everything
import * as chainSdk from "@akashnetwork/chain-sdk/web";
```

Most bundlers (Vite, Webpack 5, esbuild) tree-shake properly when you use named imports.

## Common pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| `window.keplr is undefined` | Loaded before extension is injected | Listen for the `keplr_keystorechange` event or poll briefly on load |
| Tx rejected silently | User dismissed the popup | Check for `userRejected` in the error code |
| `denom uakt rejected` | Stale SDL | Use `uact` |
| `Failed to fetch` on provider call | Browser CORS / cert pinning | Route through a provider-proxy server |
| Wrong chain id | Hardcoded mainnet on testnet | Use `"akashnet-2"` for mainnet, `"sandbox-01"` for sandbox |

## See also

- **@installation.md** — Setup, subpaths, exports
- **@chain-node-sdk.md** — Node-side equivalent flows
- **@provider-sdk.md** — Provider client, JWT, manifest push
- **@../../deploy/console-api/operations.md** — Provider URL templates (useful when running your own provider-proxy)
