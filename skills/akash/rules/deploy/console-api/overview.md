# Console API Overview

The Console API is the REST surface behind [Akash Console](https://console.akash.network). An API key authenticates as a Console account, and that account's managed wallet funds and signs every deployment action. This file covers the deployment-management subset; the rest of the spec powers the Console UI.

With `akt` installed, `akt deploy` and the `akt console` commands make these calls for you: see [../akt/overview.md](../akt/overview.md).

## Base URL and spec

```
https://console-api.akash.network
```

Every path carries its own version prefix: `/v1/...` for almost everything, `/v2/deployment-settings` for runtime limits.

| Resource | URL |
|---|---|
| OpenAPI spec (JSON) | `https://console-api.akash.network/v1/doc` |
| Swagger UI | `https://console-api.akash.network/v1/swagger` |
| Official API reference | [akash.network/docs/api-documentation/console-api/api-reference](https://akash.network/docs/api-documentation/console-api/api-reference/) |

**The live spec is the contract.** It flags deprecated endpoints and fields with `deprecated: true` and describes each error case per endpoint. If this skill, the official reference and the spec disagree, trust the spec; the reference can trail a release by weeks.

## Authentication

| Credential | Header | Use |
|---|---|---|
| **API key** (`ac.sk.production.…`) | `x-api-key: <key>` | Scripts, CI/CD, backends |
| Console session JWT | `Authorization: Bearer <jwt>` | The Console web app's own login session; not for scripts |

**Never put an API key in `Authorization: Bearer`.** Keys are created in the Console UI; see **@authentication.md**. Calls to a *provider* (logs, shell, status) use a different JWT, minted by `POST /v1/create-jwt-token`; see **@operations.md**.

## Envelopes

**Requests.** Write endpoints wrap the payload in `data`:

```json
{ "data": { "sdl": "version: \"2.0\"\n..." } }
```

Three endpoints take a flat body instead: `POST /v1/leases`, `POST /v1/bid-screening` and `POST /v1/confidential-compute/attestation/validate`.

**Responses.** Account and deployment endpoints answer `{ "data": ... }`. A few answer with the object itself: `GET /v1/providers`, `GET /v1/providers/{address}`, `GET /v1/placement-options`, `POST /v1/bid-screening`, `GET /v1/blockchain-status` and `POST /v1/confidential-compute/attestation/validate`. So a provider's URL is `.hostUri`, not `.data.hostUri`.

## Errors

Every error body has the same shape:

```json
{
  "error": "BadRequestError",
  "message": "Validation error",
  "code": "validation_error",
  "type": "validation_error",
  "data": [ ... ]
}
```

Branch on the HTTP status, then on `code` where it is specific. `message` is for humans and changes wording without notice. When a status has no specific code, `code` is the generic one for it: `bad_request`, `unauthorized`, `payment_required`, `forbidden`, `not_found`, `conflict`, `rate_limited`, `service_unavailable` or `internal_server_error`. A request that fails schema validation answers 400 `validation_error`, with the failing fields in `data`.

The specific codes a deployment script should handle:

| Status | `code` | Meaning | Do this |
|---|---|---|---|
| 402 | `insufficient_balance` | Not enough available credit to fund a new deployment. `data.requiredAmountUsd` and `data.availableAmountUsd` give the shortfall. | Add credits in the Console UI, then retry |
| 402 | `balance_top_up_pending` | Auto recharge is already charging the card for the shortfall | Wait `Retry-After` seconds, then retry |
| 402 | `payment_required` | The fee allowance ran out, or a free-trial account asked for a GPU the trial doesn't allow | Add credits; trial accounts upgrade by adding credits |
| 502 | `provider_unreachable` | `POST /v1/leases`: the provider did not answer. No lease was created. | Choose another bid |
| 502 | `manifest_not_delivered` | `POST /v1/leases`: the lease exists but the provider did not take the manifest | Send the identical request again, or close the deployment |
| 422 | `deployment_resources_changed` | An update tried to change compute resources, replica counts, groups or globally exposed ports | Create a new deployment instead |
| 409 | `deployment_definition_changed` | A concurrent `PATCH` changed the deployment first | Re-read the deployment, then re-send |

`PATCH /v1/deployments/{dseq}` and the secrets flow have a few more; they are listed next to those endpoints in **@deployment-endpoints.md** and **@secrets.md**.

## Pagination and rate limits

- `GET /v1/deployments` pages by offset: `skip` plus `limit` (at most 100), and the response carries `data.pagination.hasMore`. `GET /v1/activities` pages by cursor (`nextCursor`).
- On `429`, wait for `Retry-After` and back off exponentially. Don't hard-code a request budget: limits are set server-side and change.

## Endpoint map

| Task | Endpoint | Reference |
|---|---|---|
| Create a deployment | `POST /v1/deployments` | @deployment-endpoints.md |
| List or read deployments | `GET /v1/deployments`, `GET /v1/deployments/{dseq}` | @deployment-endpoints.md |
| Change image, env, command, ports or name | `PATCH /v1/deployments/{dseq}` | @deployment-endpoints.md |
| Close a deployment | `DELETE /v1/deployments/{dseq}` | @deployment-endpoints.md |
| List bids, accept bids | `GET /v1/bids?dseq=`, `POST /v1/leases` | @deployment-endpoints.md |
| Runtime limit | `GET`, `PATCH /v2/deployment-settings/{dseq}` | @deployment-endpoints.md |
| Provider details, regions, GPU availability | `GET /v1/providers/{address}`, `GET /v1/placement-options` | @deployment-endpoints.md |
| Secrets that can't be read back | `GET /v1/sdl-secrets-context` + `sealedSecrets` | @secrets.md |
| Balance and funding | `GET /v1/balances` | @account-and-funding.md |
| API keys | `/v1/api-keys` | @authentication.md |
| Logs, events, status, shell, attestation | `POST /v1/create-jwt-token`, then the provider | @operations.md |

For a linear walkthrough from an API key to a running deployment: **@api-key-quickstart.md**.

## Deprecated: don't generate code for these

| Deprecated | Use instead |
|---|---|
| `PUT /v1/deployments/{dseq}` (resubmits the whole SDL) | `PATCH /v1/deployments/{dseq}` |
| `manifest` in the `POST /v1/leases` body | Leave it out. Console sends the manifest it recorded when the deployment was created. |
| `POST /v1/deposit-deployment`, and `deposit` on create | Nothing. Console funds every deployment from the account's credits. |
| `POST /v1/certificates` (always answers 400) | Nothing. The API key replaces mTLS certificates. |

## UI-internal endpoints: not covered

The spec also exposes endpoints that exist to power the Console UI. They change without notice; don't write code against them.

| Surface | Endpoint pattern | Instead |
|---|---|---|
| Signup, login, email verification, account deletion | `/v1/auth/*`, `/v1/register-user`, `/v1/send-verification-*`, `/v1/verify-email*`, `/v1/user/me/*-deletion` | Console UI |
| Stripe payments, adding credits, Auto recharge | `/v1/stripe/*`, `/v1/wallet-settings` | Console UI → Billing |
| Profile, favorites, saved templates, newsletter | `/v1/user/*`, `/v1/favorite-providers` | Console UI |
| Alerts and notification channels | `/v1/alerts/*`, `/v1/deployment-alerts/*`, `/v1/notification-channels/*` | Console UI → Alerts |
| Deploy-flow drafts, hardware requests, feed state | `/v1/configure-drafts/*`, `/v1/hardware-requests`, `/v1/activities/seen` | Console UI |
| Legacy UI signing | `/v1/tx` (accepts six message types) | The dedicated deployment endpoints |
| Dashboards, analytics, explorer | `/v1/dashboard-data`, `/v1/graph-data/*`, `/v1/bme/*`, `/v1/blocks/*`, `/v1/transactions/*`, `/v1/validators/*`, `/v1/proposals/*`, `/v1/gpu*`, `/v1/provider-dashboard/*`, `/v1/market-data/*` | Console UI, or a chain node for raw chain data |
| Template gallery | `/v1/templates-list`, `/v1/templates/{id}` | [awesome-akash](https://github.com/akash-network/awesome-akash) |

## Related files

- **@authentication.md** — API keys: format, creation, CRUD, CI/CD
- **@deployment-endpoints.md** — Every deployment endpoint with bodies, responses and errors
- **@secrets.md** — `ac-secret://` references and sealed secrets
- **@api-key-quickstart.md** — From an API key to a running deployment
- **@account-and-funding.md** — Account model, balance, automatic funding, 402s
- **@operations.md** — Provider JWT, logs, events, status, shell, attestation
