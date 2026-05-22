# Console API Quickstart — From API Key to Running Deployment

A linear walkthrough for the "I have an API key" path. No CLI binaries, no certificate setup, no private-key management.

> **Pick a language first.** This file shows the flow in **curl + Bash** because it's the most universal — but if you're integrating from Node, Python, Go, or anything else, the SDK assistant should rewrite the same steps in that language before showing them to you. Don't blindly hand a user a Bash script when their integration is a Next.js app. Ask first if the user hasn't said.

If you don't have an API key yet, follow **@authentication.md** § "Getting an API key" first.

## What you need

- An API key, **stored in an environment variable, never pasted inline**. The canonical name is `AKASH_API_KEY`.
- A funded Console account (≥ $5 USD balance is enough for a small test deployment).
- An SDL file. We'll use `deploy.yaml`.

Optional: `jq` for parsing JSON responses.

### Setting up the env var (skip if already done)

| Where you'll run this | How to set the key |
|---|---|
| **Local shell** (one-off) | `export AKASH_API_KEY="..."` — won't persist across shells |
| **Local shell** (persistent) | Add `export AKASH_API_KEY="..."` to `~/.zshrc` / `~/.bashrc`, or use a `.env` file + `direnv`/`dotenv` |
| **`.env` file** | `AKASH_API_KEY=...` in `.env`; **add `.env` to `.gitignore` immediately** |
| **GitHub Actions** | Settings → Secrets and variables → Actions → New secret `AKASH_API_KEY`; reference as `${{ secrets.AKASH_API_KEY }}` |
| **GitLab CI** | Settings → CI/CD → Variables → add `AKASH_API_KEY` (mask + protect) |
| **Docker** | `docker run -e AKASH_API_KEY=$AKASH_API_KEY ...` at runtime — **never** `ARG`/`ENV` in the Dockerfile (bakes into image history) |
| **Production** | AWS Secrets Manager / GCP Secret Manager / Vault / etc. — fetch at startup, expose to the process as an env var |

Once set, you should be able to run `echo "${AKASH_API_KEY:+set}"` and see `set` (without echoing the value). All examples below assume the env var exists.

## Step 1 — Write the SDL

`deploy.yaml`:

```yaml
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
        cpu:
          units: 0.5
        memory:
          size: 512Mi
        storage:
          size: 1Gi
  placement:
    dcloud:
      pricing:
        web:
          denom: uact
          amount: 1000

deployment:
  web:
    dcloud:
      profile: web
      count: 1
```

(See `../../sdl/` for full SDL syntax. Note `denom: uact` — the new native denom; `uakt` is the old name and is no longer recognized.)

## Step 2 — Create the deployment

```bash
SDL=$(cat deploy.yaml)
RESPONSE=$(curl -sX POST https://console-api.akash.network/v1/deployments \
  -H "x-api-key: $AKASH_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -nc --arg sdl "$SDL" '{data: {sdl: $sdl, deposit: 5}}')")

echo "$RESPONSE" | jq .
```

Save the values you'll need next:

```bash
DSEQ=$(echo "$RESPONSE" | jq -r .data.dseq)
MANIFEST=$(echo "$RESPONSE" | jq -r .data.manifest)
echo "Deployment $DSEQ created"
```

`deposit: 5` is **USD**, not `5uact`. The Console API converts to the chain denom server-side.

## Step 3 — Wait for bids and list them

Bids arrive within ~5–30 seconds. Poll until you see at least one:

```bash
for i in 1 2 3 4 5 6; do
  BIDS=$(curl -s https://console-api.akash.network/v1/bids/$DSEQ \
    -H "x-api-key: $AKASH_API_KEY")
  COUNT=$(echo "$BIDS" | jq '.data | length')
  echo "Attempt $i: $COUNT bid(s)"
  [ "$COUNT" -gt 0 ] && break
  sleep 5
done

echo "$BIDS" | jq '.data[] | {provider: .bid_id.provider, price: .price.amount}'
```

If you don't get bids, the SDL might not match any provider's resources or pricing. Use the standalone `akash-bid-matcher` skill, or hit `POST /v1/bid-screening` to diagnose.

## Step 4 — Accept the cheapest bid (and send the manifest)

```bash
PROVIDER=$(echo "$BIDS" | jq -r '.data | sort_by(.price.amount | tonumber) | .[0].bid_id.provider')
GSEQ=$(echo "$BIDS" | jq -r '.data | sort_by(.price.amount | tonumber) | .[0].bid_id.gseq')
OSEQ=$(echo "$BIDS" | jq -r '.data | sort_by(.price.amount | tonumber) | .[0].bid_id.oseq')

curl -sX POST https://console-api.akash.network/v1/leases \
  -H "x-api-key: $AKASH_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -nc \
    --arg manifest "$MANIFEST" \
    --argjson dseq "$DSEQ" \
    --argjson gseq "$GSEQ" \
    --argjson oseq "$OSEQ" \
    --arg provider "$PROVIDER" \
    '{manifest: $manifest, leases: [{dseq: $dseq, gseq: $gseq, oseq: $oseq, provider: $provider}]}')" \
  | jq .
```

`POST /v1/leases` is a **batch** endpoint and it sends the manifest in the same call — there's no separate "send manifest" step.

## Step 5 — Read the deployment status (forwarded ports, IPs)

```bash
sleep 15  # let the provider start the container

curl -s https://console-api.akash.network/v1/deployments/$DSEQ \
  -H "x-api-key: $AKASH_API_KEY" \
  | jq '.data.leases[0].status'
```

You'll see `services` (with health counts), `forwarded_ports` (per-service host:port mappings), and `ips` (if you requested an IP lease in the SDL).

To extract the public URL of the `web` service:

```bash
curl -s https://console-api.akash.network/v1/deployments/$DSEQ \
  -H "x-api-key: $AKASH_API_KEY" \
  | jq -r '.data.leases[0].status.forwarded_ports.web[0] | "http://\(.host):\(.externalPort)"'
```

## Step 6 — Stream logs and events

The Console API does **not** serve logs directly. Logs come from the provider, gated by a JWT. See **@operations.md** for the full flow — the short version:

```bash
# Mint a provider-access JWT
JWT=$(curl -sX POST https://console-api.akash.network/v1/create-jwt-token \
  -H "x-api-key: $AKASH_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"data":{"ttl":1800,"leases":{"access":"scoped","scope":["status","logs","events"]}}}' \
  | jq -r .data.token)

# Resolve the provider's hostUri (cannot be derived from the deployment object)
HOSTURI=$(curl -s https://console-api.akash.network/v1/providers/$PROVIDER | jq -r .data.hostUri)

# Logs are served via WebSocket — use websocat or your language's WS client
websocat "wss://${HOSTURI#https://}/lease/$DSEQ/$GSEQ/$OSEQ/logs" \
  -H "Authorization: Bearer $JWT"
```

Note the provider URL is the provider's own host, not `console-api.akash.network`. There is no Console-API passthrough for logs.

Cert-pinning gotcha: the provider's TLS cert is verified against the on-chain wallet address rather than a CA. Standard HTTPS clients will reject it. See **@operations.md** for the Node.js / Go workaround (custom HTTPS agent + cert-fingerprint validation via `@akashnetwork/chain-sdk`).

## Step 7 — Update or close

Push a new SDL to the same deployment (keeps the lease):

```bash
NEW_SDL=$(cat deploy.v2.yaml)
curl -X PUT https://console-api.akash.network/v1/deployments/$DSEQ \
  -H "x-api-key: $AKASH_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -nc --arg sdl "$NEW_SDL" '{data: {sdl: $sdl}}')"
```

Close the deployment when you're done:

```bash
curl -X DELETE https://console-api.akash.network/v1/deployments/$DSEQ \
  -H "x-api-key: $AKASH_API_KEY"
```

## What you didn't have to do

- Install the `akash` CLI binary
- Run `akash keys add`
- Manage a private key, mnemonic, or hardware wallet
- Generate or maintain mTLS certificates (those are deprecated for the Console API path — see `../certificates/mtls-legacy.md`)
- Acquire AKT manually — your account is funded with USD via Stripe

This is the value proposition of the Console API. If a step in your workflow ever requires one of those things, you've drifted into the CLI or SDK path and should re-read SKILL.md's "Choosing a Deployment Method" section.

## Common pitfalls

| Symptom | Likely cause | Fix |
|---|---|---|
| `401 Unauthorized` | API key in `Authorization: Bearer` | Move to `x-api-key` header |
| `400 Bad Request` on create | Body not wrapped in `{ "data": { ... } }` | Wrap it |
| `400 Bad Request` on create | `deposit` sent as `"5uact"` string | Send as USD number (e.g. `5`) |
| No bids | SDL resources don't match providers; price too low | Run `POST /v1/bid-screening` or use `akash-bid-matcher` |
| `404` on lease endpoints | Tried `/lease/{dseq}/{gseq}/{oseq}` | Read lease state from `GET /v1/deployments/{dseq}.leases[]` instead |
| Logs request times out | Hit `console-api.akash.network` for logs | Logs are served by the provider — see step 6 |
| Provider TLS cert rejected | Used standard HTTPS verification | Use identity-pinned validation (chain-sdk helper) or run provider-proxy |

## Related files

- **@overview.md** — Architectural overview, response envelope, the curated subset
- **@authentication.md** — API key + JWT details
- **@deployment-endpoints.md** — Full endpoint reference
- **@account-and-funding.md** — Account model, balances, Stripe funding
- **@operations.md** — Logs, events, status, shell after the deployment is running
- **@../certificates/mtls-legacy.md** — Why you don't need certificates on this path
