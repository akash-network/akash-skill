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
                          (TLS cert pinned to provider's wallet address)
```

What you do **not** do:

- Call `console-api.akash.network/v1/proxy/...` — no such endpoint exists.
- Call the provider via the browser with standard fetch — the provider's TLS cert is self-signed, and identity is validated against the on-chain wallet address, not a CA. Browsers will reject it.

If you're in a browser, you'll typically route through a separate **provider-proxy** service (the Console runs one at `apps/provider-proxy/` in the [console monorepo](https://github.com/akash-network/console)). For server-side use you can either run your own provider-proxy or call the provider directly using a custom HTTPS agent that does cert-fingerprint validation.

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
    agent: new https.Agent({
      rejectUnauthorized: false,
      // validate the leaf cert's CN/SAN matches the provider's wallet address
      // see @akashnetwork/chain-sdk's CertificateManager (certificateManager.parsePem)
    }),
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

## Cert-pinning workaround

The provider's TLS leaf cert must match the provider's on-chain wallet address — not a CA. Standard HTTPS clients won't accept it.

**Node.js — Custom HTTPS agent.**

> ⚠️ **Illustrative pattern, not copy-paste code.** The exact mTLS verification API is evolving in `@akashnetwork/chain-sdk` (currently `@alpha`); confirm symbols against the [chain-sdk source](https://github.com/akash-network/chain-sdk) before shipping. Two real constraints the SDK forces on you:
>
> 1. **`certificateManager.parsePem` is `async`** (it lazy-loads `jsrsasign` and returns `Promise<CertificateInfo>`). Node's `checkServerIdentity` callback is **synchronous** — you cannot `await` inside it. Parse and compare the CN **outside** the TLS callback.
> 2. **There is no `subjectCommonName` field.** `CertificateInfo` exposes `sSubject` (a DN string such as `/CN=akash1...`), plus `sIssuer`, `hSerial`, `sNotBefore`, `sNotAfter`, `issuedOn`, `expiresOn`. Extract the CN from `sSubject` yourself.
> 3. **`parsePem` wants a PEM string**, but `checkServerIdentity` hands you `cert.raw` as **DER** — convert DER→PEM first.

```typescript
import https from "https";
import tls from "tls";
// certificateManager is re-exported from the package root in @akashnetwork/chain-sdk@alpha.
import { certificateManager } from "@akashnetwork/chain-sdk";

// Extract the CN from a DN string like "/CN=akash1abc...".
function cnFromSubject(sSubject: string): string | undefined {
  return sSubject
    .split("/")
    .map((p) => p.trim())
    .find((p) => p.startsWith("CN="))
    ?.slice(3);
}

// async — cannot run inside the synchronous checkServerIdentity callback.
async function providerCnMatches(derCert: Buffer, providerAddress: string): Promise<boolean> {
  const pem =
    "-----BEGIN CERTIFICATE-----\n" +
    derCert.toString("base64").match(/.{1,64}/g)!.join("\n") +
    "\n-----END CERTIFICATE-----\n";
  const info = await certificateManager.parsePem(pem); // Promise<CertificateInfo>
  return cnFromSubject(info.sSubject) === providerAddress;
}

// Pin against the leaf cert captured during the handshake (synchronous),
// then verify the CN asynchronously BEFORE you trust the response.
let leafDer: Buffer | undefined;
const agent = new https.Agent({
  rejectUnauthorized: false,
  checkServerIdentity: (_host, cert: tls.PeerCertificate) => {
    leafDer = cert.raw; // DER bytes; defer the actual CN check to after connect
    return undefined;
  },
});

const res = await fetch(`${hostUri}/lease/${dseq}/${gseq}/${oseq}/status`, {
  headers: { Authorization: `Bearer ${jwt}` },
  agent,
});
if (!leafDer || !(await providerCnMatches(leafDer, providerAddress))) {
  throw new Error("provider cert CN does not match on-chain address");
}
```

**Go — Custom TLS config:**
```go
tlsConfig := &tls.Config{
    InsecureSkipVerify: true,
    VerifyPeerCertificate: func(rawCerts [][]byte, _ [][]*x509.Certificate) error {
        // parse rawCerts[0] and verify subject CN matches providerAddress
        return validateProviderCert(rawCerts[0], providerAddress)
    },
}
transport := &http.Transport{TLSClientConfig: tlsConfig}
client := &http.Client{Transport: transport}
```

**Browser — Use a proxy.** The browser cannot do identity-pinned verification with arbitrary host certs. Run `provider-proxy` (the Node service in the Console monorepo at `apps/provider-proxy/`) or your own equivalent that handles the cert validation server-side and exposes a CORS-friendly endpoint to the browser.

The hosted public URL of the Console team's provider-proxy (if any) is not stable in the docs; check the current Console environment configuration. Do not hardcode a URL you can't verify.

## Putting it together — full Node.js example

```typescript
import WebSocket from "ws";
import https from "https";
import { certificateManager } from "@akashnetwork/chain-sdk";

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

// 4. Stream logs from the provider
//
// NOTE: certificateManager.parsePem is ASYNC (Promise<CertificateInfo>) and CertificateInfo
// has no subjectCommonName — extract the CN from its `sSubject` DN string. Because
// checkServerIdentity is synchronous, capture the leaf cert here and verify the CN once the
// socket opens (see the "Cert-pinning workaround" section for cnFromSubject/providerCnMatches).
let leafDer: Buffer | undefined;
const agent = new https.Agent({
  rejectUnauthorized: false,
  checkServerIdentity: (_host, cert) => {
    leafDer = cert.raw; // DER bytes; CN verified asynchronously below
    return undefined;
  },
});

const wss = hostUri.replace(/^https?:\/\//, "");
const ws = new WebSocket(
  `wss://${wss}/lease/${dseq}/${gseq}/${oseq}/logs?follow=true&tail=100`,
  {
    headers: { Authorization: `Bearer ${jwt}` },
    agent,
  }
);
ws.on("open", async () => {
  if (!leafDer || !(await providerCnMatches(leafDer, provider))) {
    ws.close();
    throw new Error("provider cert CN does not match on-chain address");
  }
});
ws.on("message", (chunk) => process.stdout.write(chunk));
ws.on("close", () => process.exit(0));
```

## Common pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| 401 from provider | Wrong JWT or scope missing | Re-mint with the right scope (e.g. include `"logs"`) |
| 404 on `/events` | Used `events` path — alias is client-side only | Use `/kubeevents` |
| Connection refused | Wrong `hostUri` | Always resolve from `GET /v1/providers/{address}` |
| TLS cert rejected | Standard CA validation | Use identity-pinned validation or a proxy |
| Logs empty | Deployment hasn't started | Wait; check `/status` first |
| JWT expired mid-stream | `ttl` too short | Re-mint and reconnect |
| Tried to hit Console API for logs | No passthrough exists | Provider serves logs, Console API only mints the JWT |

## Related files

- **@authentication.md** — JWT minting details, API Keys CRUD
- **@deployment-endpoints.md** — Where to read `provider`, `gseq`, `oseq` from
- **@api-key-quickstart.md** — End-to-end with logs at the end
- **@../../sdk/typescript/** — Higher-level wrappers around the provider proxy flow
- **AEP-64** — https://akash.network/roadmap/aep-64/ — JWT spec
