# Provider SDK & Provider-Direct Calls

Communicating with Akash providers using `@akashnetwork/chain-sdk`.

The provider surface in `chain-sdk` is intentionally small — `getStatus` / `streamStatus` only. Everything else (logs, events, manifest push, shell) is done by:
1. Minting an AEP-64 JWT with `JwtTokenManager`.
2. Calling the provider's HTTPS / WSS endpoints directly with `fetch` / `WebSocket` / `undici`.

## What `createProviderSDK` gives you

```typescript
import { createProviderSDK } from "@akashnetwork/chain-sdk";

const provider = createProviderSDK({
  baseUrl: hostUri,        // from sdk.akash.provider.v1beta4 query or Console API
  // auth: { type: "jwt", token } | { type: "mtls", certPem, keyPem }
});

// One-shot status
const status = await provider.getStatus();

// Streaming status (resilient)
for await (const status of provider.streamStatus()) {
  console.log(status);
}
```

For anything beyond status, see the patterns below.

## Mint a JWT

### Self-custody (recommended for chain-sdk users)

```typescript
import { JwtTokenManager } from "@akashnetwork/chain-sdk";

const jwtMgr = new JwtTokenManager(signer);  // signer from createStargateClient
const jwt = await jwtMgr.generateToken({
  iss: address,
  iat: Math.floor(Date.now() / 1000),
  exp: Math.floor(Date.now() / 1000) + 1800,
  version: "v1",
  leases: {
    access: "scoped",
    scope: ["status", "logs", "events", "shell"],
  },
});
```

The JWT payload follows [AEP-64](https://akash.network/roadmap/aep-64/). The `leases` claim has three forms:

```typescript
// Full
{ access: "full", scope: ["status", "logs", ...] }

// Scoped
{ access: "scoped", scope: ["logs"] }

// Granular
{
  access: "granular",
  permissions: [{
    provider: "akash1prov...",
    access: "scoped",
    scope: ["logs"],
    deployments: [{ dseq: "12345678", gseq: 1, scope: ["logs"] }],
  }],
}
```

Valid scopes: `send-manifest`, `get-manifest`, `logs`, `shell`, `events`, `status`, `restart`. Grant the minimum.

### Managed wallet (Console API users)

You don't have the key — Console signs the JWT for you:

```bash
curl -X POST https://console-api.akash.network/v1/create-jwt-token \
  -H "x-api-key: $AKASH_API_KEY" \
  -d '{"data":{"ttl":1800,"leases":{"access":"scoped","scope":["logs"]}}}'
```

See **@../../deploy/console-api/authentication.md**.

## Resolve the provider's `hostUri`

The deployment object gives you the provider's address, not the URL:

```typescript
// From the SDK
const lease = await sdk.akash.market.v1beta5.getLeases({
  filters: { owner: address, dseq, state: "active" },
});
const providerAddress = lease.leases[0].lease.leaseId.provider;

const prov = await sdk.akash.provider.v1beta4.provider({ owner: providerAddress });
const hostUri = prov.provider.hostUri;
```

```bash
# Or via the Console API
curl https://console-api.akash.network/v1/providers/$PROVIDER \
  | jq -r .data.hostUri
```

## Provider TLS — skip verification for now

Provider TLS certs are self-signed (not issued by a public CA), so standard HTTPS clients reject them. Authentication is the JWT — there's no client certificate to manage. For direct, server-side provider calls, disable TLS verification:

```typescript
import https from "node:https";
import { fetch, Agent } from "undici";

const agent = new Agent({
  connect: { rejectUnauthorized: false },
});

// Then pass `dispatcher: agent` to undici fetch.
```

For Node's built-in `https` module:

```typescript
const httpsAgent = new https.Agent({ rejectUnauthorized: false });
```

Don't hand-roll CN-matching against the provider's on-chain address — first-class provider-certificate verification is coming to `@akashnetwork/chain-sdk`. In the browser, route through a provider proxy instead (see **@chain-web-sdk.md**).

## Stream logs

Logs are served via WebSocket on the provider:

```
wss://<hostUri-without-https>/lease/<dseq>/<gseq>/<oseq>/logs
```

Query params (optional): `follow=true`, `tail=<n>`, `service=<svc-name>`.

```typescript
import WebSocket from "ws";

const wss = hostUri.replace(/^https?:\/\//, "");
const ws = new WebSocket(
  `wss://${wss}/lease/${dseq}/${gseq}/${oseq}/logs?follow=true&tail=200`,
  {
    headers: { Authorization: `Bearer ${jwt}` },
    agent: httpsAgent,  // TLS-verification-disabled agent from above
  }
);

ws.on("message", (chunk) => process.stdout.write(chunk));
ws.on("close", () => console.log("Logs stream closed"));
ws.on("error", (err) => console.error("Logs error:", err));
```

## Stream events

The provider path is `/kubeevents`, not `/events` (the Console UI aliases the latter to the former — that alias is client-side only):

```typescript
const ws = new WebSocket(
  `wss://${wss}/lease/${dseq}/${gseq}/${oseq}/kubeevents`,
  {
    headers: { Authorization: `Bearer ${jwt}` },
    agent: httpsAgent,
  }
);
```

## Read lease status

This is what `createProviderSDK().getStatus()` does under the hood; you can also call it manually:

```typescript
const res = await fetch(
  `${hostUri}/lease/${dseq}/${gseq}/${oseq}/status`,
  {
    headers: { Authorization: `Bearer ${jwt}` },
    dispatcher: agent,
  }
);
const status = await res.json();
console.log(status.services, status.forwardedPorts, status.ips);
```

## Push a manifest

After `createLease`, push the manifest so the provider starts the workload:

```typescript
const res = await fetch(
  `${hostUri}/deployment/${dseq}/manifest`,
  {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${jwt}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(manifest),  // from generateManifest()
    dispatcher: agent,
  }
);
```

The JWT needs `send-manifest` scope for this.

## Shell into a running pod

```
wss://<hostUri>/lease/<dseq>/<gseq>/<oseq>/shell?service=<svc>&podIndex=<n>&cmd=<base64-cmd>
```

The protocol is a binary multiplexed stream (stdin/stdout/stderr/resize). Use a library like `xterm-headless` or implement the framing yourself; the Console web app uses `xterm.js`. The JWT needs `shell` scope.

## Restart a service

The `restart` scope authorizes:

```
POST {hostUri}/lease/{dseq}/{gseq}/{oseq}/services/{service}/restart
```

## Common pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| 401 from provider | Wrong JWT or scope missing | Re-mint with the right scope, set `Authorization: Bearer` |
| 404 on `/events` | Used the alias | Use `/kubeevents` |
| Cert rejected | Provider cert is self-signed | Set `rejectUnauthorized: false` (server-side) or use a provider proxy (browser) |
| Logs hang then close | `follow=true` plus an idle service | Normal; reconnect on close |
| Stream stops mid-session | JWT expired | Increase `ttl` or refresh by minting a new JWT |
| 403 on `send-manifest` | JWT lacks scope | Re-mint with `scope: ["send-manifest", ...]` |
| Calling Console API for logs | Wrong service | Logs come from the provider; Console API only mints the JWT |

## See also

- **@installation.md** — Install + dependencies
- **@chain-node-sdk.md** — Full deploy flow ending with `createLease`
- **@chain-web-sdk.md** — Browser flow; provider calls usually need a proxy
- **@../../deploy/console-api/operations.md** — Same patterns in curl form
- **AEP-64** — https://akash.network/roadmap/aep-64/
