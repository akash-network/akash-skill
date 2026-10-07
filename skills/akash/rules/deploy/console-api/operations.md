# Operations — Logs, Events, Status, Shell and Attestation

Once a deployment runs, logs, Kubernetes events, live status, shell access and TEE attestation all come from the **provider**, not from `console-api.akash.network`. Each call carries a short-lived JWT. Managed-wallet users mint it with the Console API; self-custody users sign it locally. Everything after minting is identical.

```
your client ──HTTPS/WSS, Authorization: Bearer <jwt>──▶ provider hostUri
```

There is no Console API passthrough: `console-api.akash.network/v1/proxy/...` and `/v1/logs/...` don't exist.

## Step 1 — Find the lease and the provider's hostUri

```bash
DEPL=$(curl -s "https://console-api.akash.network/v1/deployments/$DSEQ" -H "x-api-key: $AKASH_API_KEY")
PROVIDER=$(echo "$DEPL" | jq -r '.data.leases[0].id.provider')
GSEQ=$(echo "$DEPL" | jq -r '.data.leases[0].id.gseq')
OSEQ=$(echo "$DEPL" | jq -r '.data.leases[0].id.oseq')

HOSTURI=$(curl -s "https://console-api.akash.network/v1/providers/$PROVIDER" | jq -r '.hostUri')
```

`GET /v1/providers/{address}` is public and returns the provider object itself, so it's `.hostUri`, not `.data.hostUri`. The provider's on-chain record is the only source of the URL; don't derive it from anything else. A deployment with several groups has one lease per group; pick the lease by `gseq` and `oseq`.

## Step 2 — Mint a JWT

### Managed wallet (Console API)

```bash
JWT=$(curl -sX POST https://console-api.akash.network/v1/create-jwt-token \
  -H "x-api-key: $AKASH_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"data": {"ttl": 1800, "leases": {"access": "scoped", "scope": ["status", "logs", "events"]}}}' \
  | jq -r .data.token)
```

`ttl` is in seconds and required; the Console UI uses 1800. There is no refresh endpoint: mint a new token when one expires. The response is `201 { "data": { "token": "<jwt>" } }`.

### Self-custody (CLI or SDK)

Console can't sign for a key it doesn't hold. Sign locally with `@akashnetwork/chain-sdk`:

```typescript
import { JwtTokenManager } from "@akashnetwork/chain-sdk";

const jwt = await new JwtTokenManager(wallet).generateToken({
  version: "v1",
  iss: address,
  exp: Math.floor(Date.now() / 1000) + 1800,
  leases: { access: "scoped", scope: ["status", "logs", "events"] }
});
```

`iat` and `nbf` default to now. The payload follows [AEP-64](https://akash.network/roadmap/aep-64/), and the provider checks it the same way whoever signed it.

### The `leases` claim

Three shapes; the JWT schema rejects anything else.

```json
{ "access": "full" }
```

Every action on every lease you own. **`full` takes no `scope`**; adding one makes the token invalid.

```json
{ "access": "scoped", "scope": ["logs", "status"] }
```

The listed actions on every lease you own.

```json
{
  "access": "granular",
  "permissions": [
    { "provider": "akash1provA...", "access": "scoped", "scope": ["logs", "status"] },
    {
      "provider": "akash1provB...",
      "access": "granular",
      "deployments": [{ "dseq": 1785245500842, "gseq": 1, "oseq": 1, "services": ["web"], "scope": ["shell"] }]
    }
  ]
}
```

Per provider: `full`, `scoped` with a `scope`, or `granular` with `deployments`. Each `deployments` entry needs `dseq` (a number), `scope` and `services` (at least one service name); `gseq` and `oseq` are optional. Each provider may appear once.

**Scopes:** `send-manifest`, `get-manifest`, `logs`, `shell`, `events`, `status`, `restart`, `hostname-migrate`, `ip-migrate`, `attestation`. Grant the narrowest set that works: a token with `shell` can read the container's environment, sealed secrets included.

## Step 3 — Call the provider

All paths sit under `{hostUri}/lease/{dseq}/{gseq}/{oseq}`.

### Status (HTTPS)

```bash
curl -sk "$HOSTURI/lease/$DSEQ/$GSEQ/$OSEQ/status" -H "Authorization: Bearer $JWT"
```

Scope `status`. Returns per-service readiness, forwarded ports and IPs, freshly polled: the same data as `leases[].status` in `GET /v1/deployments/{dseq}`.

### Logs (WebSocket)

```
WSS {hostUri}/lease/{dseq}/{gseq}/{oseq}/logs?follow=true&tail=200&service=web
```

Scope `logs`. `follow`, `tail` and `service` are optional.

```bash
websocat -k "wss://${HOSTURI#https://}/lease/$DSEQ/$GSEQ/$OSEQ/logs?follow=true&tail=200" \
  -H "Authorization: Bearer $JWT"
```

### Events (WebSocket)

```
WSS {hostUri}/lease/{dseq}/{gseq}/{oseq}/kubeevents
```

Scope `events`. These are the Kubernetes events of the deployment's pods: image pulls, crash loops, scheduling failures. The path is always `kubeevents`; `events` is only an alias inside the Console UI.

### Shell (WebSocket)

```
WSS {hostUri}/lease/{dseq}/{gseq}/{oseq}/shell?service=<svc>&podIndex=<n>&tty=0&stdin=0&cmd0=<arg0>&cmd1=<arg1>...
```

Scope `shell`. Required query params: `service`, `podIndex`, `tty` (`1` or `0`), `stdin` (`1` or `0`), and the command as separate numbered params `cmd0`, `cmd1`, … (`cmd0=/bin/sh&cmd1=-c&cmd2=ls`). There is no single `cmd` param, and nothing is base64-encoded.

Frames are binary, and the **first byte is the stream code**: from the server `100` stdout, `101` stderr, `102` result (JSON such as `{"exit_code":0}`), `103` failure; from the client `104` stdin, `105` terminal resize. Strip the first byte before printing the payload.

```typescript
import WebSocket from "ws";
import https from "https";

const params = new URLSearchParams({ service, podIndex: "0", tty: "0", stdin: "0" });
["/bin/sh", "-c", "echo hello && hostname"].forEach((arg, i) => params.append(`cmd${i}`, arg));

const ws = new WebSocket(`wss://${hostUri.replace(/^https?:\/\//, "")}/lease/${dseq}/${gseq}/${oseq}/shell?${params}`, {
  headers: { Authorization: `Bearer ${jwt}` },
  agent: new https.Agent({ rejectUnauthorized: false })
});
ws.on("message", (frame: Buffer) => {
  const code = frame[0], data = frame.subarray(1);
  if (code === 100) process.stdout.write(data);
  else if (code === 101) process.stderr.write(data);
  else if (code === 102) { console.log("result:", data.toString()); ws.close(); }
});
```

That is a one-shot command. For an interactive session set `tty=1&stdin=1`, send keystrokes as `104`-prefixed frames and resizes as `105` frames, or use `provider-services lease-shell --tty` (see [Shell Access](https://akash.network/docs/learn/core-concepts/shell-access/)).

### Attestation (Confidential Compute)

For a deployment with `params.tee` (see `rules/sdl/confidential-compute.md`), the provider returns hardware-signed evidence, and the Console API checks it against the hardware vendors.

1. Mint a JWT with the `attestation` scope.
2. Ask the provider for a quote, sending a fresh nonce of 64 random bytes, base64-encoded:

   ```bash
   NONCE=$(openssl rand -base64 64 | tr -d '\n')
   QUOTE=$(curl -skX POST "$HOSTURI/lease/$DSEQ/$GSEQ/$OSEQ/attestation/quote?service=web" \
     -H "Authorization: Bearer $JWT" \
     -H "Content-Type: application/json" \
     -d "$(jq -nc --arg nonce "$NONCE" '{nonce: $nonce, bind_tls: false}')")
   ```

   The response carries `report`, `tee_platform` (`snp`, `tdx`, `snp-gpu` or `tdx-gpu`), `cert_chain`, `auxblob` and, on GPU platforms, `gpu_reports`. `service` and `podIndex` pick the pod; both are optional.

3. Validate it, sending the same nonce:

   ```bash
   curl -sX POST https://console-api.akash.network/v1/confidential-compute/attestation/validate \
     -H "x-api-key: $AKASH_API_KEY" \
     -H "Content-Type: application/json" \
     -d "$(echo "$QUOTE" | jq -c --arg nonce "$NONCE" '{nonce: $nonce, report, tee_platform, cert_chain: (.cert_chain // ""), auxblob: (.auxblob // ""), gpu_reports: (.gpu_reports // [])}')"
   ```

   The body is flat. The answer has `overall` (`valid`, `invalid` or `unverifiable`) and one verdict per report under `reports`, with `checks` for the certificate chain, signature, nonce binding and revocation. `unverifiable` means a check couldn't run, for example because a vendor service was unreachable; it is not a failure of the hardware.

### Push a manifest (HTTPS PUT)

```
PUT {hostUri}/deployment/{dseq}/manifest
```

Scope `send-manifest`. Managed-wallet users never call this: `POST /v1/leases` and `PATCH /v1/deployments/{dseq}` send manifests for you. Self-custody users usually let the SDK do it.

## Provider TLS

Providers serve HTTPS with a **self-signed** certificate, so default HTTPS clients reject it. The JWT is the authentication; there is no client certificate to manage (the old mTLS flow is in **@../cli/mtls-legacy.md**).

For direct, server-side calls, turn certificate verification off for the provider connection only: `curl -k`, `websocat -k`, `tls.Config{InsecureSkipVerify: true}` in Go. In Node it depends on the client:

- `ws` WebSockets take `agent: new https.Agent({ rejectUnauthorized: false })`, as in the examples on this page.
- `fetch` ignores `agent`. Use the `undici` package (`npm install undici`) and pass its `Agent` as `dispatcher`:

  ```typescript
  import { Agent, fetch } from "undici";

  const dispatcher = new Agent({ connect: { rejectUnauthorized: false } });
  try {
    const res = await fetch(`${hostUri}/lease/${dseq}/${gseq}/${oseq}/status`, {
      headers: { Authorization: `Bearer ${jwt}` },
      dispatcher
    });
    console.log(await res.json());
  } finally {
    await dispatcher.close();
  }
  ```

Don't hand-roll a check of the certificate against the provider's on-chain address; first-class provider-certificate verification is planned for `@akashnetwork/chain-sdk`.

Browsers can't skip verification. A browser app routes through a provider proxy, a server that holds the provider connection and exposes a CORS-friendly endpoint; Console runs one built from `apps/provider-proxy/` in the [console monorepo](https://github.com/akash-network/console). Its hosted URL is not a public contract, so don't hard-code it.

## Full Node.js example: stream logs

```typescript
import WebSocket from "ws";
import https from "https";

const API = "https://console-api.akash.network";
const headers = { "x-api-key": process.env.AKASH_API_KEY!, "Content-Type": "application/json" };
const dseq = process.env.DSEQ!;

const { data: deployment } = await (await fetch(`${API}/v1/deployments/${dseq}`, { headers })).json();
const { provider, gseq, oseq } = deployment.leases[0].id;

const { hostUri } = await (await fetch(`${API}/v1/providers/${provider}`)).json();

const { data: jwt } = await (
  await fetch(`${API}/v1/create-jwt-token`, {
    method: "POST",
    headers,
    body: JSON.stringify({ data: { ttl: 1800, leases: { access: "scoped", scope: ["logs"] } } })
  })
).json();

const ws = new WebSocket(`wss://${hostUri.replace(/^https?:\/\//, "")}/lease/${dseq}/${gseq}/${oseq}/logs?follow=true&tail=100`, {
  headers: { Authorization: `Bearer ${jwt.token}` },
  agent: new https.Agent({ rejectUnauthorized: false })
});
ws.on("message", chunk => process.stdout.write(chunk.toString()));
ws.on("close", () => process.exit(0));
```

## Common pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| 401 or 403 from the provider | Token expired, or its scope lacks the action | Mint a new token with the needed scope |
| 400 from `create-jwt-token` | Malformed `leases` claim, such as `scope` on `access: "full"` | Use one of the three shapes above |
| 404 on `/events` | `events` is a UI alias | Use `/kubeevents` |
| Connection refused | Wrong host | Resolve `hostUri` from `GET /v1/providers/{address}` |
| TLS certificate rejected | Provider certificate is self-signed | Skip verification server-side, or use a provider proxy |
| Empty log stream | The workload hasn't started | Check `/status` first |
| Stream dies after a while | The token expired | Mint a new one and reconnect |
| Attestation quote fails | Not a TEE deployment, or no `attestation` scope | Check `params.tee` in the SDL and the token's scope |

## Related files

- **@authentication.md** — API keys
- **@deployment-endpoints.md** — Where `provider`, `gseq` and `oseq` come from
- **@api-key-quickstart.md** — End to end, with logs at the end
- **@../../sdk/typescript/provider-sdk.md** — The same flow through the SDK's provider client
- **AEP-64** — https://akash.network/roadmap/aep-64/ — the JWT specification
