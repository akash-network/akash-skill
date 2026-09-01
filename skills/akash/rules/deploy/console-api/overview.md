# Console API Overview

The Akash Console API provides REST endpoints for programmatic deployments backed by a Console-managed wallet.

This document covers the **deployment-management subset** of the Console API. The live OpenAPI spec at `https://console-api.akash.network/v1/doc` exposes ~100 endpoints across ~27 tags — most are Console-UI internals (Stripe payments, user signup, alerts, blockchain explorer queries, GPU stats, analytics) and are not part of the supported deployment contract.

## Base URL

```
https://console-api.akash.network/v1
```

## OpenAPI documentation

- **Full spec (JSON):** `https://console-api.akash.network/v1/doc`
- **Swagger UI:** `https://console-api.akash.network/v1/swagger`
- **Official API reference:** [akash.network/docs/api-documentation/console-api/api-reference](https://akash.network/docs/api-documentation/console-api/api-reference/)

The full Swagger spec mixes deployment endpoints with Console-UI internals. If you only need the deployment management contract, use this skill's curated reference in `deployment-endpoints.md`.

## Two stability tiers — read this before you write code

Endpoints in this skill fall into two tiers. Code against the higher tier; treat the lower tier as best-effort.

**Tier 1 — Documented in the official API reference.** The Akash team commits to these as the supported programmatic surface. 13 endpoints total:

- Deployments — `POST /v1/deployments`, `GET /v1/deployments`, `GET /v1/deployments/{dseq}`, `PUT /v1/deployments/{dseq}`, `DELETE /v1/deployments/{dseq}`
- Escrow — `POST /v1/deposit-deployment` (deprecated; funding is automatic)
- Leases — `POST /v1/leases`
- Bids — `GET /v1/bids?dseq=`
- Deployment settings / runtime limits — `GET /v2/deployment-settings/{dseq}`, `POST /v2/deployment-settings`, `PATCH /v2/deployment-settings/{dseq}`
- Providers (public, no auth) — `GET /v1/providers`, `GET /v1/providers/{address}`

**Tier 2 — Swagger-only / undocumented.** Observed on the running Console API service but **not** in the official reference. They may change or be removed without notice. The skill documents them for completeness because some are genuinely useful (e.g., `GET /v1/balances`, `POST /v1/create-jwt-token` for the logs flow), but you should pin to a tested runtime version and watch for breakage on Console releases. Examples: `/v1/balances`, `/v1/create-jwt-token`, `/v1/api-keys` CRUD, `/v1/bid-screening`, `/v1/blockchain-status`, `/v1/weekly-cost`, `/v1/deployment/{owner}/{dseq}`, `/v1/provider-regions`, `/v1/provider-versions`, `/v1/provider-attributes-schema`, `/v1/auditors`.

Each Tier-2 endpoint in this skill carries a "Swagger-only" banner at the section that documents it. If you're building something critical, prefer Tier-1 paths and use the UI for what Tier 2 covers.

## Authentication

Two schemes are supported. Use whichever fits your client:

| Scheme | Header | When |
|---|---|---|
| **API key** | `x-api-key: <key>` | Server-to-server, CI/CD, scripts |
| **JWT (session)** | `Authorization: Bearer <jwt>` | Browser sessions, short-lived access |

**Do not** put an API key in `Authorization: Bearer` — that header is reserved for JWTs.

Read **@authentication.md** for the full auth flow including API Keys CRUD and JWT minting via `POST /v1/create-jwt-token`.

## Request envelope

All write endpoints wrap their payload in a `data` object:

```json
{ "data": { ... } }
```

For example, creating a deployment:

```json
{
  "data": {
    "sdl": "version: \"2.0\"\n..."
  }
}
```

No `deposit`: Console funds the deployment from the account's credit balance. A caller-supplied deposit is ignored, and the field is deprecated.

## Quick start

### 1. Create an account and get an API key

1. Visit https://console.akash.network and sign up.
2. Add credits to your account (Stripe).
3. Generate an API key under Settings → API Keys. Copy it once — the plaintext key is shown exactly one time.

### 2. Create a deployment

```bash
curl -X POST https://console-api.akash.network/v1/deployments \
  -H "x-api-key: $AKASH_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "sdl": "version: \"2.0\"\nservices:\n  web:\n    image: nginx:1.25.3\n    expose:\n      - port: 80\n        as: 80\n        to:\n          - global: true\nprofiles:\n  compute:\n    web:\n      resources:\n        cpu:\n          units: 0.5\n        memory:\n          size: 512Mi\n        storage:\n          size: 1Gi\n  placement:\n    dcloud:\n      pricing:\n        web:\n          denom: uact\n          amount: 1000\ndeployment:\n  web:\n    dcloud:\n      profile: web\n      count: 1"
    }
  }'
```

The response contains a `dseq` (deployment sequence number), the manifest the server prepared, and the broadcast result of the `MsgCreateDeployment` transaction.

### 3. List bids

```bash
curl "https://console-api.akash.network/v1/bids?dseq=<dseq>" \
  -H "x-api-key: $AKASH_API_KEY"
```

Or by query string: `GET /v1/bids?dseq=<dseq>`.

### 4. Accept bids and send the manifest (one call)

```bash
curl -X POST https://console-api.akash.network/v1/leases \
  -H "x-api-key: $AKASH_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "manifest": "<manifest from create response>",
    "leases": [
      { "dseq": <dseq>, "gseq": 1, "oseq": 1, "provider": "akash1..." }
    ]
  }'
```

This is a **batch** endpoint — there is no single-lease creation endpoint. The manifest is sent in the same call.

### 5. Read deployment state (status, ports, IPs, lease URIs)

```bash
curl https://console-api.akash.network/v1/deployments/<dseq> \
  -H "x-api-key: $AKASH_API_KEY"
```

The response includes `leases[].status.forwarded_ports` and `leases[].status.ips`, which is how you discover the running service's URL.

### 6. Stream logs and events

Logs and events are not served by the Console API directly — they come from the **provider**, gated by a JWT minted via `/v1/create-jwt-token`. See **@operations.md** for the full flow.

## Response shape

Successful responses from the deployment endpoints return:

```json
{ "data": { ... endpoint-specific payload ... } }
```

Errors typically include an HTTP status and a JSON body with `code` and `message`. The exact error envelope varies by endpoint; rely on the HTTP status to branch.

## Rate limits

Rate limits exist and depend on your account tier; the exact numbers are managed by the Console team and can change. Implement exponential backoff for `429 Too Many Requests` responses (use the `Retry-After` header if present).

## Endpoint summary (curated deployment subset)

| Group | Methods | Endpoints | See |
|---|---|---|---|
| Deployments | CRUD + update | 10 paths under `/v1/deployments` and `/v1/deposit-deployment` | @deployment-endpoints.md |
| Leases | Batch create | `POST /v1/leases` | @deployment-endpoints.md |
| Bids | List | `GET /v1/bids?dseq=` | @deployment-endpoints.md |
| Providers | Read | `GET /v1/providers`, `GET /v1/providers/{address}`, ... | @deployment-endpoints.md |
| Bid screening | Match deployment to providers | `POST /v1/bid-screening` | @deployment-endpoints.md |
| API Keys | CRUD | `/v1/api-keys` | @authentication.md |
| JWT minting | Provider-access tokens | `POST /v1/create-jwt-token` | @authentication.md, @operations.md |
| Account & funding | Read-only balance + per-deployment runtime limits (signup, adding credits, and arbitrary tx signing are UI-only) | `GET /v1/balances`, `/v2/deployment-settings/*` | @account-and-funding.md |
| Operations | Logs, events, status, shell (via provider proxy) | provider URL templates | @operations.md |

For the curated reference: **@deployment-endpoints.md**.

For a linear walkthrough from "I have an API key" to a running deployment: **@api-key-quickstart.md**.

## What is NOT covered here

The full Swagger exposes ~80 additional endpoints that this skill intentionally omits because they are **Console-UI internals**, not a stable public API. Do not write code against them — use the Console UI for these operations instead.

| UI-only surface | Endpoint pattern | Use the UI for… |
|---|---|---|
| Account creation, auth, email verification | `/v1/auth/signup`, `/v1/register-user`, `/v1/send-verification-email`, `/v1/verify-email`, `/v1/verify-email-code`, `/v1/send-verification-code` | Sign up, log in, password reset, email verification |
| Trial wallet provisioning | `/v1/start-trial` | First-time wallet creation (handled implicitly by signup in the UI) |
| **Stripe payments and transactions** | `/v1/stripe/*` (payment methods, transactions, customer, coupons) | Adding cards, adding credits, viewing billing history |
| Account-level Auto Top-Up | `/v1/wallet-settings`, `/v1/deployment-settings/*` (v1) | Settings → Auto Top-Up, which charges the card to keep the credit balance up. (Per-deployment runtime limits via `/v2/deployment-settings/*` *are* programmatic — see @deployment-endpoints.md.) |
| Username & profile management | `/v1/user/me`, `/v1/user/updateSettings`, username availability checks | Editing your profile |
| Favorite / saved templates | `/v1/user/addFavoriteTemplate`, `/v1/user/saveTemplate`, etc. | Bookmarking templates in the Console UI |
| Alerts and notification channels | `/v1/alerts/*`, `/v1/deployment-alerts/*`, `/v1/notification-channels/*` | Configuring deployment health alerts |
| Newsletter | `/v1/newsletter/*` | Email subscriptions |
| Dashboard analytics | `/v1/bme/*`, `/v1/dashboard-data`, `/v1/network-capacity`, `/v1/graph-data/*`, `/v1/provider-graph-data/*`, `/v1/provider-dashboard/*`, `/v1/provider-earnings/*`, `/v1/leases-duration/*`, `/v1/market-data/*` | Browsing dashboards in the UI |
| Blockchain explorer | `/v1/blocks/*`, `/v1/validators/*`, `/v1/proposals/*`, `/v1/transactions/*`, `/v1/addresses/{address}/*`, `/v1/predicted-*`, `/v1/gpu*` | Chain inspection in the UI |
| Templates listing | `/v1/templates-list`, `/v1/templates/{id}` | Browsing the template marketplace |

These endpoints exist to power the Console UI and may change without notice. They are not part of the deployment-management contract this skill documents.

## Related files

- **@authentication.md** — `x-api-key` vs JWT, API Keys CRUD, JWT minting
- **@deployment-endpoints.md** — Full endpoint reference with bodies and examples
- **@api-key-quickstart.md** — End-to-end walkthrough for the API-key path
- **@account-and-funding.md** — Account model, programmatic balance reads, automatic deployment funding; signup, adding credits, and arbitrary tx signing are UI-only
- **@operations.md** — Post-deploy: logs, events, status, shell, manifest updates
