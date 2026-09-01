# Console API — Deployment Endpoint Reference

Curated reference for the deployment-management subset of the Console API. All endpoints are under `https://console-api.akash.network/v1`. Authentication is `x-api-key: <key>` unless otherwise noted.

All write endpoints wrap payloads in `{ "data": { ... } }`.

## Quick links

- [Deployments](#deployments)
- [Leases](#leases)
- [Bids](#bids)
- [Bid screening](#bid-screening)
- [Providers](#providers)
- [Deployment settings v2 (runtime limits)](#deployment-settings-v2-runtime-limits)

For API keys and JWT minting, see **@authentication.md**. For logs/events/status from the provider, see **@operations.md**.

## Deployments

### Create deployment

```
POST /v1/deployments
```

**Auth:** `x-api-key`

**Body:**
```json
{
  "data": {
    "sdl": "<SDL as a string with literal \\n newlines>"
  }
}
```

- `sdl` — full SDL YAML as a string
- `runtimeLimitHours` — optional integer, 1 to 48. Closes the deployment after that many hours of runtime, counted from lease start, and returns the unused credits. Omit it for always-on funding.

Do **not** send a `deposit`. Console funds every deployment from the account's credit balance and ignores a caller-supplied amount. The field is deprecated and will be removed.

**Response (201):**
```json
{
  "data": {
    "dseq": "12345678",
    "manifest": "<manifest the server prepared>",
    "signTx": {
      "code": 0,
      "transactionHash": "0xabc...",
      "rawLog": "..."
    }
  }
}
```

The `manifest` field is what you pass to `POST /v1/leases` later — keep it.

**Example:**
```bash
SDL=$(cat deploy.yaml)
curl -X POST https://console-api.akash.network/v1/deployments \
  -H "x-api-key: $AKASH_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -nc --arg sdl "$SDL" '{data: {sdl: $sdl}}')"
```

### List deployments

```
GET /v1/deployments?skip=0&limit=100
```

**Auth:** `x-api-key`

**Query:**
- `skip` — pagination offset (default 0)
- `limit` — page size (default 1000, max varies)

**Response:** array of deployments scoped to your account.

### Get deployment

```
GET /v1/deployments/{dseq}
```

**Auth:** `x-api-key`

**Response:**
```json
{
  "data": {
    "deployment": { "id": {...}, "state": "active", ... },
    "leases": [
      {
        "id": { "owner": "akash1...", "dseq": "12345678", "gseq": 1, "oseq": 1, "provider": "akash1prov..." },
        "state": "active",
        "price": { "denom": "uact", "amount": "1000" },
        "status": {
          "services": { "web": { "available": 1, "total": 1, "uris": [...] } },
          "forwarded_ports": { "web": [{ "host": "...", "port": 80, "externalPort": 31234 }] },
          "ips": [...]
        }
      }
    ],
    "escrow_account": {
      "id": { "scope": "deployment", "xid": "..." },
      "state": { "owner": "akash1...", "state": "open", "funds": [{ "denom": "uact", "amount": "..." }], "settled_at": "..." }
    }
  }
}
```

This is the canonical place to read **forwarded ports**, **IPs**, and **provider addresses** for a running deployment.

### Update deployment (push new SDL)

```
PUT /v1/deployments/{dseq}
```

**Auth:** `x-api-key`

**Body:**
```json
{ "data": { "sdl": "<new SDL>" } }
```

Re-broadcasts a `MsgUpdateDeployment` to the chain with the new manifest. The lease stays in place; the provider re-applies the manifest.

### Close deployment

```
DELETE /v1/deployments/{dseq}
```

**Auth:** `x-api-key`

Closes the deployment on-chain and settles escrow. Whatever the deployment has not spent returns to the account's credit balance.

### Deposit additional funds (deprecated)

> ⚠️ **Deprecated.** Console tops every deployment up automatically for as long as the account has credits, so there is nothing for this endpoint to do. It still accepts requests, and will be removed. Do not generate code that calls it — if an account is running low, the fix is adding credits, which is a UI action. See [How Funding Works](https://akash.network/docs/getting-started/how-funding-works/).

```
POST /v1/deposit-deployment
```

**Auth:** `x-api-key`

**Body:**
```json
{ "data": { "dseq": "12345678", "deposit": 5 } }
```

### Public read-only deployment view

> ⚠️ **Swagger-only (Tier 2).** Not in the [official API reference](https://akash.network/docs/api-documentation/console-api/api-reference/). For authenticated, supported deployment reads use `GET /v1/deployments/{dseq}` instead.

```
GET /v1/deployment/{owner}/{dseq}
```

**Auth:** Public (no auth required)

Read-only deployment lookup by owner address + dseq. Returns the on-chain state, lease info, monthly cost, and recent events. Useful for status pages and external dashboards.

### Weekly cost

> ⚠️ **Swagger-only (Tier 2).** Not in the [official API reference](https://akash.network/docs/api-documentation/console-api/api-reference/). May change without notice.

```
GET /v1/weekly-cost
```

**Auth:** `x-api-key`

Returns the USD weekly cost of the account's automatically funded deployments.

## Leases

The Console API has **one** lease endpoint — and it's batch. There is no single-lease creation endpoint.

### Create leases + send manifest

```
POST /v1/leases
```

**Auth:** `x-api-key`

**Body:** **flat** — this is the one exception in the API; the body is NOT wrapped in `{ "data": { ... } }`.

```json
{
  "manifest": "<manifest from the create-deployment response>",
  "leases": [
    { "dseq": 12345678, "gseq": 1, "oseq": 1, "provider": "akash1providerA..." },
    { "dseq": 12345678, "gseq": 2, "oseq": 1, "provider": "akash1providerB..." }
  ]
}
```

This single call:
1. Broadcasts a `MsgCreateLease` for each item in `leases`.
2. Sends the manifest to each chosen provider.

**Bid identity gotcha:** when you copy a bid from the bids list response into the `leases` array, take **only** `dseq`, `gseq`, `oseq`, `provider`. The bid object also contains `owner` and `bseq` — those are not part of the lease payload and including them is unnecessary.

**Example (one provider):**
```bash
curl -X POST https://console-api.akash.network/v1/leases \
  -H "x-api-key: $AKASH_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "manifest": "'"$MANIFEST"'",
    "leases": [{"dseq": 12345678, "gseq": 1, "oseq": 1, "provider": "akash1providerA..."}]
  }'
```

### Closing a lease

There is no `DELETE /v1/lease/...` endpoint. To close a lease, close the entire deployment via `DELETE /v1/deployments/{dseq}` — that's the only documented way. Closing an individual lease while keeping the deployment open is not exposed as a programmatic endpoint.

### Reading lease state

There is no `GET /v1/lease/...` either. Lease state — current bid price, escrow balance, service status, forwarded ports, IPs — is returned by `GET /v1/deployments/{dseq}` under `leases[]`. Use that.

## Bids

### List bids for a deployment

```
GET /v1/bids?dseq={dseq}
```

**Auth:** `x-api-key`

This is the canonical form documented in the official API reference. A path-parameter variant (`GET /v1/bids/{dseq}`) may be exposed by the running service but is **not in the official docs** — use the query-string form.

**Response:** an array of items under `data[]`. Each item in `data[]` contains a `bid` object (and an `escrow_account`):

```json
{
  "bid": {
    "id": { "owner": "akash1...", "dseq": "...", "gseq": 1, "oseq": 1, "provider": "akash1prov..." },
    "state": "open",
    "price": { "denom": "uact", "amount": "1500" },
    "created_at": "...",
    "resources_offer": [
      {
        "resources": {
          "cpu": { "units": { "val": "500" } },
          "memory": { "quantity": { "val": "536870912" } },
          "storage": [{ "quantity": { "val": "1073741824" } }],
          "gpu": { "units": { "val": "0" } }
        },
        "count": 1
      }
    ]
  },
  "escrow_account": {
    "id": { "scope": "bid", "xid": "..." },
    "state": {
      "owner": "akash1...",
      "state": "open",
      "funds": [{ "denom": "uact", "amount": "..." }],
      "settled_at": "..."
    }
  }
}
```

`resources_offer` is the per-unit compute the provider committed to. Useful for verifying that a provider can actually run what the SDL requested before you accept the bid.

## Bid screening

> ⚠️ **Swagger-only (Tier 2).** Not in the [official API reference](https://akash.network/docs/api-documentation/console-api/api-reference/). Powers the bid-matching workflow in this skill (see `rules/bid-matching/`); useful for pre-flight checks but not a stable contract.

### Match a deployment's compute requirements against providers

```
POST /v1/bid-screening
```

**Auth:** Public (no auth required)

**Body:**
```json
{
  "name": "screening-1",
  "requirements": {
    "signedBy": { "allOf": [], "anyOf": [] },
    "attributes": []
  },
  "resources": [
    {
      "resources": {
        "cpu": { "units": { "val": "500" } },
        "memory": { "quantity": { "val": "536870912" } },
        "storage": [{ "quantity": { "val": "1073741824" } }],
        "gpu": { "units": { "val": "0" } }
      },
      "count": 1
    }
  ]
}
```

**Response:**
```json
{
  "providers": [
    { "owner": "akash1...", "hostUri": "https://provider.example:8443", "region": "us-west", "uptime7d": 0.99, "isAudited": true }
  ]
}
```

This is the live engine behind the bid-matching workflow in this skill (see `rules/bid-matching/`). Use it to predict whether an SDL will get bids before broadcasting.

## Providers

### List providers

```
GET /v1/providers
```

**Auth:** Public

Returns all known providers, including offline ones.

### Provider details

```
GET /v1/providers/{address}
```

**Auth:** Public

Returns the provider's `hostUri`, attributes, region, uptime, audit status, and resource inventory. This is where you get the **hostUri** for streaming logs (see **@operations.md**).

There is no `GET /v1/providers/{address}/status` — that endpoint was removed. Status fields are merged into `GET /v1/providers/{address}`.

### Provider regions / versions / attributes schema / auditors

> ⚠️ **Swagger-only (Tier 2).** Only `GET /v1/providers` and `GET /v1/providers/{address}` are in the [official API reference](https://akash.network/docs/api-documentation/console-api/api-reference/). The four endpoints below are observed on the running service but may change without notice. Useful for SDL placement-attribute editors.

```
GET /v1/provider-regions
GET /v1/provider-versions
GET /v1/provider-attributes-schema
GET /v1/auditors
```

All public; useful for SDL placement attribute editors.

## Deployment settings v2 (runtime limits)

Read and change a deployment's funding settings. Documented in the official API reference.

Automatic funding is always on and cannot be turned off: `autoTopUpEnabled` is accepted for backwards compatibility, and an explicit `false` is rejected. What these endpoints are actually for is the **runtime limit** — an optional cap on how long a deployment runs before Console closes it and returns the unused credits.

### Get deployment settings

```
GET /v2/deployment-settings/{dseq}
```

**Auth:** `x-api-key`

Returns the current settings for the deployment. The record is auto-created on first read. Response includes `runtimeLimitHours` (`null` for always-on funding), `runtimeEndsAt` (`null` until the lease starts), `autoTopUpEnabled`, `estimatedTopUpAmount`, and `topUpFrequencyMs`.

### Create deployment settings

```
POST /v2/deployment-settings
```

**Auth:** `x-api-key`

**Body:**
```json
{ "data": { "dseq": "12345678" } }
```

Returns 201 on success. Only needed when the settings row does not exist yet; a `GET` creates it too.

### Update deployment settings

```
PATCH /v2/deployment-settings/{dseq}
```

**Auth:** `x-api-key`

**Body:**
```json
{ "data": { "runtimeLimitHours": 48 } }
```

Send the new **total**, not an increment, and raise it by at most 48 hours per request. Lowering a limit is not supported. Send `null` to drop the limit and return the deployment to always-on funding.

> The older `/v1/deployment-settings/*` paths are not documented in the official API reference; use the **v2** endpoints. Account-level Auto Top-Up (`/v1/wallet-settings`), which charges the card to keep the credit balance up, is **UI-only**.

## What is gone vs. older docs

For anyone migrating from older skill versions, here is the change set:

| Old (stale) | New (current) |
|---|---|
| `POST /deployment` | `POST /v1/deployments` |
| `GET /deployment/{dseq}` | `GET /v1/deployments/{dseq}` |
| `DELETE /deployment/{dseq}` | `DELETE /v1/deployments/{dseq}` |
| `POST /deployment/{dseq}/deposit` | Gone — deployments are funded automatically. `POST /v1/deposit-deployment` still exists but is deprecated |
| `GET /providers/{address}/status` | merged into `GET /v1/providers/{address}` |
| `POST /lease` (single) | `POST /v1/leases` (batch + manifest) |
| `GET /lease/{dseq}/{gseq}/{oseq}` | read from `GET /v1/deployments/{dseq}.leases[]` |
| `DELETE /lease/{dseq}/{gseq}/{oseq}` | not exposed; close the entire deployment via `DELETE /v1/deployments/{dseq}` instead |
| `POST /sdl/validate` | does not exist — validate client-side |
| `POST /sdl/price` | does not exist — no pricing endpoint; actual prices come from provider bids (`GET /v1/bids?dseq=`) |
| `POST /wallet/create` | Account creation is **UI-only** at [console.akash.network](https://console.akash.network) — no API for first-time signup (see @account-and-funding.md) |
| `GET /wallet/balance` | `GET /v1/balances?address=...` |
| `POST /wallet/deposit` | Adding credits happens in the Console UI via Stripe; **no programmatic endpoint** (see @account-and-funding.md) |
| `Authorization: Bearer <api-key>` | `x-api-key: <key>` |
| `POST /v1/auth/refresh` | does not exist — re-mint via `POST /v1/create-jwt-token` |
