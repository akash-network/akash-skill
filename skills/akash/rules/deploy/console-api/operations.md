# Operations — Logs, Events, Status, and Shell

> ⚠️ **Mixed stability.** The managed-wallet path on this page depends on `POST /v1/create-jwt-token`, which is **Swagger-only / Tier 2** — observed on the live service but not in the [official API reference](https://akash.network/docs/api-documentation/console-api/api-reference/). It may change without notice. For production log/shell workflows on the managed-wallet path, you may want to use the Console UI's built-in viewers and treat the API flow below as best-effort. The self-custody path (signing the JWT locally with `@akashnetwork/chain-sdk`) is fully supported and not subject to this caveat.

Once a deployment is running, you need to read **logs**, watch **events**, check **status**, and occasionally **exec into the container**. None of this is served by `console-api.akash.network` — it all comes from the **provider** directly, gated by a short-lived JWT.

This page covers the full post-deploy operational loop. It applies equally to managed-wallet users (Console API path) and self-custody users (CLI/SDK path) — the only difference is how you mint the JWT.

## The architecture

```
your client  ─────────────────────┐
                                  │ HTTPS / WSS
                                  │ Authorization: Bearer <jwt>
                                  ▼
                          provider hostUri
                          (self-signed TLS cert; auth is the JWT)
```

What you do **not** do:

- Call `console-api.akash.network/v1/proxy/...` — no such endpoint exists.
- Call the provider via the browser with standard fetch — the provider's TLS cert is self-signed (not issued by a public CA), so browsers reject it.

If you're in a browser, you'll typically route through a separate **provider-proxy** service (the Console runs one at `apps/provider-proxy/` in the [console monorepo](https://github.com/akash-network/console)) — it terminates and validates the provider connection server-side. For server-side use you can either run your own provider-proxy or call the provider directly with TLS verification disabled (`rejectUnauthorized: false`); see below.

## Step 1 — Resolve the provider's hostUri

The deployment object gives you the provider's **address**, not the URL. Resolve the URL separately:

```bash
DEPL=$(curl -s https://console-api.akash.network/v1/deployments/$DSEQ \
  -H "x-api-key: $AKASH_API_KEY")

PROVIDER=$(echo "$DEPL" | jq -r '.data.leases[0].id.provider')
GSEQ=$(echo "$DEPL" | jq -r '.data.leases[0].id.gseq')
OSEQ=$(echo "$DEPL" | jq -r '.data.leases[0].id.oseq')

HOSTURI=$(curl -s https://console-api.akash.network/v1/providers/$PROVIDER \
  | jq -r '.hostUri')

echo "Provider host: $HOSTURI"
```

`hostUri` is the only authoritative source — don't try to derive it from anything else.

## Step 2 — Mint a JWT

### Managed-wallet (Console API) path

```bash
JWT=$(curl -sX POST https://console-api.akash.network/v1/create-jwt-token \
  -H "x-api-key: $AKASH_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "ttl": 1800,
      "leases": {
        "access": "scoped",
        "scope": ["status", "logs", "events", "shell"]
      }
    }
  }' | jq -r .data.token)
```

`ttl` is in seconds. The default in the Console web app is 1800 (30 minutes). To refresh, re-call this endpoint — there is no `/v1/auth/refresh`.

### Self-custody (CLI/SDK) path

The Console doesn't hold your key, so it can't sign your JWT. Sign locally with `@akashnetwork/chain-sdk`:

```typescript
import { JwtTokenManager } from "@akashnetwork/chain-sdk";

const mgr = new JwtTokenManager(wallet); // wallet exposes the signing key
const jwt = await mgr.generateToken({
  iss: address,
  iat: Math.floor(Date.now() / 1000),
  exp: Math.floor(Date.now() / 1000) + 1800,
  version: "v1",
  leases: { access: "scoped", scope: ["status", "logs", "events"] }
});
```

The JWT payload follows [AEP-64](https://akash.network/roadmap/aep-64/). The provider validates it the same way regardless of who minted it.

### `leases` claim — the three forms

```json
// Full — every scope across every lease you own
{ "access": "full", "scope": ["status","logs","events","shell"] }

// Scoped — restricted scopes across every lease
{ "access": "scoped", "scope": ["logs","status"] }

// Granular — per-provider, per-deployment
{
  "access": "granular",
  "permissions": [{
    "provider": "akash1prov...",
    "access": "scoped",
    "scope": ["logs"],
    "deployments": [{ "dseq": "12345678", "gseq": 1, "scope": ["logs"] }]
  }]
}
```

Valid scope values: `send-manifest`, `get-manifest`, `logs`, `shell`, `events`, `status`, `restart`. Grant the narrowest set you need.

## Step 3 — Call the provider

All URLs below are templates rooted at `${hostUri}/lease/{dseq}/{gseq}/{oseq}/...`.

### Status (HTTP, JSON)

```bash
curl "$HOSTURI/lease/$DSEQ/$GSEQ/$OSEQ/status" \
  -H "Authorization: Bearer $JWT"
```

Returns the current state of each service: ready replicas, total replicas, forwarded ports, IP assignments, and recent restart counts. This is the same data that appears under `deployment.leases[].status` in the Console API response, but freshly polled from the provider.

### Logs (WebSocket)

```
WSS  {hostUri}/lease/{dseq}/{gseq}/{oseq}/logs
```

Query params (optional): `tail=<n>`, `follow=true`, `service=<svc-name>`.

**Example with websocat:**
```bash
websocat "wss://${HOSTURI#https://}/lease/$DSEQ/$GSEQ/$OSEQ/logs?follow=true&tail=200" \
  -H "Authorization: Bearer $JWT"
```

**Example in Node.js:**
```typescript
import WebSocket from "ws";
import https from "https";

const ws = new WebSocket(
  `wss://${hostUri.replace(/^https?:\/\//, "")}/lease/${dseq}/${gseq}/${oseq}/logs?follow=true`,
  {
    headers: { Authorization: `Bearer ${jwt}` },
    // Provider serves a self-signed cert; skip TLS verification for now.
    agent: new https.Agent({ rejectUnauthorized: false }),
  }
);
ws.on("message", (chunk) => process.stdout.write(chunk));
```

### Events (WebSocket)

```
WSS  {hostUri}/lease/{dseq}/{gseq}/{oseq}/kubeevents
```

These are the Kubernetes events for the pods running your deployment. **Important alias gotcha:** the Console UI accepts `"events"` as a path component and rewrites it to `kubeevents`. The wire path on the provider is always `kubeevents` — use that directly to avoid confusion.

### Shell (WebSocket)

```
WSS  {hostUri}/lease/{dseq}/{gseq}/{oseq}/shell?service=<svc>&podIndex=<n>&cmd=<base64-encoded-cmd>
```

Interactive exec. The protocol is a binary multiplexed stream (stdin / stdout / stderr / resize). The Console UI uses `xterm.js` on the client side. For programmatic shells, use the provider's `kubectl exec`-style protocol via the SDK helpers.

### Push a manifest (HTTP PUT)

```
PUT  {hostUri}/deployment/{dseq}/manifest
```

This is what `POST /v1/leases` does under the hood for managed-wallet users. Self-custody users typically use the SDK helper instead of constructing the call manually.

## Provider TLS — skip verification for now

Providers serve HTTPS with a **self-signed** certificate (not from a public CA), so standard HTTPS clients reject it. Authentication is handled entirely by the **JWT** (`Authorization: Bearer`) — you do **not** need an Akash client certificate; that mTLS flow is deprecated (see **@../cli/mtls-legacy.md**).

For direct, server-side provider calls, disable TLS certificate verification:

**Node.js:**
```typescript
import https from "https";

const agent = new https.Agent({ rejectUnauthorized: false });

const res = await fetch(`${hostUri}/lease/${dseq}/${gseq}/${oseq}/status`, {
  headers: { Authorization: `Bearer ${jwt}` },
  agent,
});
```

**Go:**
```go
tlsConfig := &tls.Config{InsecureSkipVerify: true}
transport := &http.Transport{TLSClientConfig: tlsConfig}
client := &http.Client{Transport: transport}
```

Don't hand-roll CN-matching of the provider's cert against its on-chain address — first-class provider-certificate verification is coming to `@akashnetwork/chain-sdk`. Until it ships, disabling verification is the supported approach for server-side code.

**Browser — use the provider proxy.** You can't disable TLS verification in a browser. Route through `provider-proxy` (the Node service in the Console monorepo at `apps/provider-proxy/`) or your own equivalent, which validates the provider connection server-side and exposes a CORS-friendly endpoint. This is what Console does today.

The hosted public URL of the Console team's provider-proxy (if any) is not stable in the docs; check the current Console environment configuration. Do not hardcode a URL you can't verify.

## Putting it together — full Node.js example

```typescript
import WebSocket from "ws";
import https from "https";

const API_BASE = "https://console-api.akash.network/v1";
const apiKey = process.env.AKASH_API_KEY!;
const dseq = process.env.DSEQ!;

// 1. Get the deployment
const depl = await (await fetch(`${API_BASE}/deployments/${dseq}`, {
  headers: { "x-api-key": apiKey },
})).json();
const lease = depl.data.leases[0];
const { provider, gseq, oseq } = lease.id;

// 2. Resolve provider hostUri
const prov = await (await fetch(`${API_BASE}/providers/${provider}`, {
  headers: { "x-api-key": apiKey },
})).json();
const hostUri = prov.hostUri;

// 3. Mint a JWT
const jwtResp = await (await fetch(`${API_BASE}/create-jwt-token`, {
  method: "POST",
  headers: { "x-api-key": apiKey, "Content-Type": "application/json" },
  body: JSON.stringify({
    data: { ttl: 1800, leases: { access: "scoped", scope: ["logs"] } },
  }),
})).json();
const jwt = jwtResp.data.token;

// 4. Stream logs from the provider (self-signed cert; skip TLS verification for now)
const agent = new https.Agent({ rejectUnauthorized: false });

const wss = hostUri.replace(/^https?:\/\//, "");
const ws = new WebSocket(
  `wss://${wss}/lease/${dseq}/${gseq}/${oseq}/logs?follow=true&tail=100`,
  {
    headers: { Authorization: `Bearer ${jwt}` },
    agent,
  }
);
ws.on("message", (chunk) => process.stdout.write(chunk));
ws.on("close", () => process.exit(0));
```

## Common pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| 401 from provider | Wrong JWT or scope missing | Re-mint with the right scope (e.g. include `"logs"`) |
| 404 on `/events` | Used `events` path — alias is client-side only | Use `/kubeevents` |
| Connection refused | Wrong `hostUri` | Always resolve from `GET /v1/providers/{address}` |
| TLS cert rejected | Provider cert is self-signed | Set `rejectUnauthorized: false` (Node) / `InsecureSkipVerify` (Go), or use the provider proxy |
| Logs empty | Deployment hasn't started | Wait; check `/status` first |
| JWT expired mid-stream | `ttl` too short | Re-mint and reconnect |
| Tried to hit Console API for logs | No passthrough exists | Provider serves logs, Console API only mints the JWT |

## Related files

- **@authentication.md** — JWT minting details, API Keys CRUD
- **@deployment-endpoints.md** — Where to read `provider`, `gseq`, `oseq` from
- **@api-key-quickstart.md** — End-to-end with logs at the end
- **@../../sdk/typescript/** — Higher-level wrappers around the provider proxy flow
- **AEP-64** — https://akash.network/roadmap/aep-64/ — JWT spec
