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

The full spec mixes deployment endpoints with Console-UI internals. If you only need the deployment management contract, use this skill's curated reference in `deployment-endpoints.md`. The Akash team may publish a filtered "public API" spec in the future.

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
    "sdl": "version: \"2.0\"\n...",
    "deposit": 5
  }
}
```

The `deposit` field is a **USD number** (e.g. `5` means $5 USD), not a denom string. Conversion to `uact` happens server-side.

## Quick start

### 1. Create an account and get an API key

1. Visit https://console.akash.network and sign up.
2. Fund your account (Stripe).
3. Generate an API key under Settings → API Keys. Copy it once — the plaintext key is shown exactly one time.

### 2. Create a deployment

```bash
curl -X POST https://console-api.akash.network/v1/deployments \
  -H "x-api-key: $AKASH_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "sdl": "version: \"2.0\"\nservices:\n  web:\n    image: nginx:1.25.3\n    expose:\n      - port: 80\n        as: 80\n        to:\n          - global: true\nprofiles:\n  compute:\n    web:\n      resources:\n        cpu:\n          units: 0.5\n        memory:\n          size: 512Mi\n        storage:\n          size: 1Gi\n  placement:\n    dcloud:\n      pricing:\n        web:\n          denom: uact\n          amount: 1000\ndeployment:\n  web:\n    dcloud:\n      profile: web\n      count: 1",
      "deposit": 5
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
| Deployments | CRUD + deposit + update | 10 paths under `/v1/deployments` and `/v1/deposit-deployment` | @deployment-endpoints.md |
| Leases | Batch create | `POST /v1/leases` | @deployment-endpoints.md |
| Bids | List | `GET /v1/bids?dseq=` | @deployment-endpoints.md |
| Pricing | Estimate | `POST /v1/pricing` | @deployment-endpoints.md |
| Providers | Read | `GET /v1/providers`, `GET /v1/providers/{address}`, ... | @deployment-endpoints.md |
| Bid screening | Match deployment to providers | `POST /v1/bid-screening` | @deployment-endpoints.md |
| API Keys | CRUD | `/v1/api-keys` | @authentication.md |
| JWT minting | Provider-access tokens | `POST /v1/create-jwt-token` | @authentication.md, @operations.md |
| Account & funding | Read-only balance + per-deployment auto-top-up (setup, funding, and arbitrary tx signing are UI-only) | `GET /v1/balances`, `/v2/deployment-settings/*` | @account-and-funding.md |
| Operations | Logs, events, status, shell (via provider proxy) | provider URL templates | @operations.md |

For the curated reference: **@deployment-endpoints.md**.

For a linear walkthrough from "I have an API key" to a running deployment: **@api-key-quickstart.md**.

## What is NOT covered here

The full Swagger exposes ~80 additional endpoints that this skill intentionally omits because they are **Console-UI internals**, not a stable public API. Do not write code against them — use the Console UI for these operations instead.

| UI-only surface | Endpoint pattern | Use the UI for… |
|---|---|---|
| Account creation, auth, email verification | `/v1/auth/signup`, `/v1/register-user`, `/v1/send-verification-email`, `/v1/verify-email`, `/v1/verify-email-code`, `/v1/send-verification-code` | Sign up, log in, password reset, email verification |
| Trial wallet provisioning | `/v1/start-trial` | First-time wallet creation (handled implicitly by signup in the UI) |
| **Stripe payments and transactions** | `/v1/stripe/*` (payment methods, transactions, customer, coupons) | Adding cards, topping up the wallet, viewing billing history |
| Account-level auto-reload | `/v1/wallet-settings`, `/v1/deployment-settings/*` (v1) | Settings → Auto-top-up. (Per-deployment auto-top-up via `/v2/deployment-settings/*` *is* programmatic — see @deployment-endpoints.md.) |
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
- **@account-and-funding.md** — Account model, programmatic balance reads, per-deployment auto-top-up; bootstrap, Stripe funding, and arbitrary tx signing are UI-only
- **@operations.md** — Post-deploy: logs, events, status, shell, manifest updates
