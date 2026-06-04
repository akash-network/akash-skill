# Chain SDK — Node.js

End-to-end deploy flows using `@akashnetwork/chain-sdk` on the server side.

If you haven't installed yet, see **@installation.md**.

## Setup

```typescript
import { createChainNodeSDK, createStargateClient } from "@akashnetwork/chain-sdk";

const signer = createStargateClient({
  baseUrl: "https://rpc.akashnet.net:443",
  signerMnemonic: process.env.MNEMONIC!,  // 12/24-word phrase
});

const sdk = createChainNodeSDK({
  query: { baseUrl: "https://grpc.akashnet.net:443" },
  tx:    { signer },
});

const address = await signer.address();
```

## Query — list your deployments

```typescript
const result = await sdk.akash.deployment.v1beta4.getDeployments({
  filters: { owner: address, state: "active" },
  pagination: { limit: 50 },
});

for (const d of result.deployments) {
  console.log(d.deployment.deploymentId.dseq, d.deployment.state);
}
```

## Create a deployment

The full flow has four logical steps:

1. Build the manifest + version from your SDL.
2. Send `MsgCreateDeployment`.
3. Wait for bids and pick one.
4. Send `MsgCreateLease` and push the manifest to the chosen provider.

### Step 1 — Generate manifest from SDL

```typescript
import { generateManifest, generateManifestVersion } from "@akashnetwork/chain-sdk";
import fs from "node:fs";

const sdlText = fs.readFileSync("./deploy.yaml", "utf-8");
const manifest = generateManifest(sdlText);
const version = generateManifestVersion(manifest);  // bytes used as on-chain hash
```

Alternatively, use the `yaml` tagged template for inline SDL:

```typescript
import { yaml, generateManifest } from "@akashnetwork/chain-sdk";

const sdlText = yaml`
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
          cpu: { units: 0.5 }
          memory: { size: 512Mi }
          storage: { size: 1Gi }
    placement:
      dcloud:
        pricing:
          web: { denom: uact, amount: 1000 }
  deployment:
    web:
      dcloud:
        profile: web
        count: 1
`;
const manifest = generateManifest(sdlText);
```

### Step 2 — Send `MsgCreateDeployment`

```typescript
import { Source } from "@akashnetwork/chain-sdk/private-types/akash.v1beta4";

const dseq = BigInt(Math.floor(Date.now() / 1000));

const createResult = await sdk.akash.deployment.v1beta4.createDeployment({
  id: { owner: address, dseq },
  groups: manifest.groups,
  version: generateManifestVersion(manifest),
  deposit: { denom: "uact", amount: "5000000" },
  depositor: address,
  // Or fund from balance via `sources`:
  // deposit: { sources: [Source.balance] },
});

console.log("Created", createResult.transactionHash, "dseq:", dseq);
```

### Step 3 — Wait for and list bids

```typescript
// Poll until we have at least one bid
async function waitForBids(dseq: bigint) {
  for (let i = 0; i < 12; i++) {
    const bids = await sdk.akash.market.v1beta5.getBids({
      filters: { owner: address, dseq, state: "open" },
    });
    if (bids.bids.length > 0) return bids.bids;
    await new Promise((r) => setTimeout(r, 5000));
  }
  throw new Error("No bids received");
}

const bids = await waitForBids(dseq);
const cheapest = bids.sort((a, b) =>
  Number(BigInt(a.bid.price.amount) - BigInt(b.bid.price.amount))
)[0];
```

Each bid exposes `bid.bidId.{owner,dseq,gseq,oseq,provider}` and `bid.price.{denom,amount}`. The `resourcesOffer` array tells you what the provider committed to.

### Step 4 — Accept the bid (create lease)

```typescript
const leaseResult = await sdk.akash.market.v1beta5.createLease({
  bidId: cheapest.bid.bidId,
});
console.log("Lease created", leaseResult.transactionHash);
```

After `createLease`, you also need to push the manifest to the provider so it actually starts the workload. The provider call is **not** part of the chain SDK — see **@provider-sdk.md** for the JWT + provider URL pattern.

## Update a deployment (push new SDL)

```typescript
const newManifest = generateManifest(fs.readFileSync("./deploy.v2.yaml", "utf-8"));
const newVersion = generateManifestVersion(newManifest);

await sdk.akash.deployment.v1beta4.updateDeployment({
  id: { owner: address, dseq },
  version: newVersion,
});

// then push newManifest to the provider — see provider-sdk.md
```

## Close a deployment

```typescript
await sdk.akash.deployment.v1beta4.closeDeployment({
  id: { owner: address, dseq },
});
```

This closes the deployment and all its leases on-chain.

## Deposit additional funds

```typescript
await sdk.akash.deployment.v1beta4.depositDeployment({
  id: { owner: address, dseq },
  amount: { denom: "uact", amount: "5000000" },
  depositor: address,
});
```

## Multi-message transactions

If you want to batch (e.g. accept a lease and create a cert in one tx):

```typescript
import { transaction, msg } from "@akashnetwork/chain-sdk";

const result = await transaction(sdk, [
  msg("akash.market.v1beta5.createLease", { bidId: cheapest.bid.bidId }),
  msg("akash.cert.v1.createCertificate", { cert: certPem, pubkey: pubKeyPem }),
], { memo: "deploy run #42" });
```

## Error handling

```typescript
import { SDKError, TxError } from "@akashnetwork/chain-sdk";

try {
  await sdk.akash.deployment.v1beta4.createDeployment({ ... });
} catch (err) {
  if (err instanceof TxError) {
    // chain-side error: insufficient gas, invalid msg, etc.
    console.error("Tx failed:", err.code, err.rawLog);
  } else if (err instanceof SDKError) {
    // network / transport issue
    console.error("SDK error:", err.code, err.message);
  } else {
    throw err;
  }
}
```

## Common pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| `MsgCreateDeployment` parse error | Wrong message version | Use `v1beta4`, not `v1beta3` |
| `MsgCreateLease` parse error | Wrong message version | Use `v1beta5`, not `v1beta4` |
| Insufficient gas | Default gas too low for SDL with many services | Pass `gas: "auto"` or set a higher limit in tx options |
| No bids | Pricing too low, or SDL resources don't match providers | Use `POST /v1/bid-screening` on the Console API; for in-skill diagnosis see `rules/bid-matching/` in the `akash` skill |
| Manifest push fails | Sent to wrong provider host | Resolve `hostUri` from `sdk.akash.audit.v1` queries or the Console API's `GET /v1/providers/{address}` |

## See also

- **@installation.md** — Setup and dependencies
- **@chain-web-sdk.md** — Browser flows
- **@provider-sdk.md** — Provider client, JWT minting, manifest push, logs
- **@../../deploy/console-api/operations.md** — Provider URL templates and JWT pattern
