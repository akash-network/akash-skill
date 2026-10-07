# Console API Quickstart — From API Key to Running Deployment

The whole flow for the API-key path: no CLI, no certificates, no private keys. It is written in curl + Bash; when the user works in Node, Python or Go, translate the same calls into their language (see SKILL.md, "Language for the Console API").

## What you need

- An API key in the environment variable `AKASH_API_KEY`. No key yet? See **@authentication.md**.
- Credits on the Console account. A few dollars covers a small test.
- An SDL file, here `deploy.yaml`, and `jq`.

### Where the key lives

| Runtime | How |
|---|---|
| Local shell | `export AKASH_API_KEY=...`, or a `.env` file loaded by `direnv`, with `.env` in `.gitignore` |
| GitHub Actions | Repository secret `AKASH_API_KEY`, exposed as `env: AKASH_API_KEY: ${{ secrets.AKASH_API_KEY }}` |
| GitLab CI | Masked, protected CI/CD variable `AKASH_API_KEY` |
| Docker | `docker run -e AKASH_API_KEY ...` at run time, never `ARG` or `ENV` in the Dockerfile |
| Production | A secrets manager that injects `AKASH_API_KEY` into the process environment |

`echo "${AKASH_API_KEY:+set}"` prints `set` without revealing the key.

## Step 1 — The SDL

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

`denom: uact` is the deployment-payment denom. SDL syntax is in `../../sdl/`.

## Step 2 — Create the deployment

```bash
API=https://console-api.akash.network
RESPONSE=$(curl -sX POST "$API/v1/deployments" \
  -H "x-api-key: $AKASH_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -nc --rawfile sdl deploy.yaml '{data: {sdl: $sdl, name: "nginx-test"}}')")

DSEQ=$(echo "$RESPONSE" | jq -r '.data.dseq')
echo "Deployment $DSEQ created"
```

No deposit: Console funds the deployment from the account's credits. A `402` here means the account is short of credit; the body's `code` says why (**@account-and-funding.md**). Secrets in `env` need nothing extra to stay out of later reads, but to seal only some values and keep the rest readable, see **@secrets.md**.

## Step 3 — Wait for bids

```bash
for i in $(seq 1 12); do
  BIDS=$(curl -s "$API/v1/bids?dseq=$DSEQ" -H "x-api-key: $AKASH_API_KEY")
  COUNT=$(echo "$BIDS" | jq '[.data[] | select(.bid.state == "open")] | length')
  [ "$COUNT" -gt 0 ] && break
  sleep 5
done

echo "$BIDS" | jq '.data[] | {provider: .bid.id.provider, price: .bid.price.amount}'
```

Bids usually arrive within 5 to 30 seconds. None after a minute means no provider matches the SDL or the price is too low: run the matcher in `rules/bid-matching/`.

## Step 4 — Accept the cheapest bid

```bash
BID=$(echo "$BIDS" | jq -c '[.data[] | select(.bid.state == "open")] | sort_by(.bid.price.amount | tonumber) | .[0].bid.id')

curl -sX POST "$API/v1/leases" \
  -H "x-api-key: $AKASH_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -nc --argjson id "$BID" '{leases: [{dseq: $id.dseq, gseq: $id.gseq, oseq: $id.oseq, provider: $id.provider}]}')" \
  | jq '.data.leases[0].id'
```

The body is flat (no `data` wrapper) and carries no manifest: Console sends the provider the manifest it recorded in step 2. If the call fails with `code: "provider_unreachable"`, no lease was made, so try the next bid. With `manifest_not_delivered` the lease exists: send the same request again.

## Step 5 — Wait until it serves, then get the URL

```bash
until curl -s "$API/v1/deployments/$DSEQ" -H "x-api-key: $AKASH_API_KEY" \
    | jq -e '.data.leases[0].status.services.web.available >= 1' > /dev/null; do
  sleep 5
done

HOST=$(curl -s "$API/v1/deployments/$DSEQ" -H "x-api-key: $AKASH_API_KEY" \
  | jq -r '.data.leases[0].status.services.web.uris[0]')
echo "http://$HOST"
```

A global expose with `as: 80` gets a hostname in `services.<svc>.uris`. Any other port appears under `forwarded_ports.<svc>` as `host` plus a random `externalPort`:

```bash
jq -r '.data.leases[0].status.forwarded_ports.api[0] | "\(.host):\(.externalPort)"'
```

## Step 6 — Logs and events

Logs come from the provider, not the Console API. The short version, with the full flow in **@operations.md**:

```bash
LEASE=$(curl -s "$API/v1/deployments/$DSEQ" -H "x-api-key: $AKASH_API_KEY" | jq '.data.leases[0].id')
PROVIDER=$(echo "$LEASE" | jq -r .provider); GSEQ=$(echo "$LEASE" | jq -r .gseq); OSEQ=$(echo "$LEASE" | jq -r .oseq)
HOSTURI=$(curl -s "$API/v1/providers/$PROVIDER" | jq -r .hostUri)

JWT=$(curl -sX POST "$API/v1/create-jwt-token" \
  -H "x-api-key: $AKASH_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"data": {"ttl": 1800, "leases": {"access": "scoped", "scope": ["logs", "events", "status"]}}}' \
  | jq -r .data.token)

websocat -k "wss://${HOSTURI#https://}/lease/$DSEQ/$GSEQ/$OSEQ/logs?follow=true&tail=200" \
  -H "Authorization: Bearer $JWT"
```

`-k` is there because providers serve self-signed certificates; the JWT is the authentication.

## Step 7 — Change it, then close it

Roll a new image, or change env, command, ports or the name, with `PATCH`. Only what you name changes:

```bash
curl -sX PATCH "$API/v1/deployments/$DSEQ" \
  -H "x-api-key: $AKASH_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"data": {"services": {"web": {"image": "nginx:1.27.2"}}}}'
```

CPU, memory, storage, GPUs and replica counts can't change in place: that needs a new deployment (**@deployment-endpoints.md**, "Patch a deployment").

Close it when you're done; unspent escrow returns to the account:

```bash
curl -sX DELETE "$API/v1/deployments/$DSEQ" -H "x-api-key: $AKASH_API_KEY"
```

## What you didn't have to do

- Install `provider-services` or run `provider-services keys add`
- Hold a private key, mnemonic or hardware wallet
- Create mTLS certificates (deprecated for this path: `../cli/mtls-legacy.md`)
- Buy AKT, or mint ACT
- Send a deposit or a manifest

If a step ever needs one of these, the workflow has drifted onto the CLI or SDK path; re-read SKILL.md, "Choosing a Deployment Method".

## Common pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| `401 Invalid API key` | Key revoked, expired or mistyped | Check it starts `ac.sk.production.`; create a new one if needed |
| `401` with a valid key | Key sent as `Authorization: Bearer` | Use `x-api-key` |
| `400 validation_error` on create | Body not wrapped in `{"data": {...}}`, or the SDL built by string splicing | Build the body with `jq --rawfile` |
| `402 insufficient_balance` | Not enough credit | Add credits in the Console UI |
| No bids | Resources or price match no provider | `rules/bid-matching/` |
| `502 provider_unreachable` on lease | The provider is down | Accept another bid |
| `PUT` used to update | Deprecated full-SDL update | `PATCH` with only the fields that change |
| `422 deployment_resources_changed` | Tried to resize in place | New deployment, then close the old one |
| URL is `null` | Read `forwarded_ports` for an `as: 80` service | Read `status.services.<svc>.uris` |
| Logs call times out | Sent to `console-api.akash.network` | Logs come from the provider (step 6) |

## Related files

- **@overview.md** — Envelopes, errors, deprecations, the endpoint map
- **@authentication.md** — API keys
- **@deployment-endpoints.md** — Every endpoint in detail
- **@secrets.md** — Sealed secrets
- **@account-and-funding.md** — Balance and automatic funding
- **@operations.md** — Logs, events, status, shell, attestation
