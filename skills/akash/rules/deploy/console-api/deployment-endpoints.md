# Console API — Deployment Endpoint Reference

Every endpoint below lives under `https://console-api.akash.network` and takes `x-api-key: <key>` unless marked public. Write endpoints wrap the body in `{ "data": { ... } }`; the exceptions are called out. The error envelope and the cross-cutting error codes are in **@overview.md**.

## Quick links

- [Deployments](#deployments): create, list, read, patch, close
- [Leases](#leases)
- [Bids](#bids)
- [Runtime limits](#runtime-limits-deployment-settings-v2)
- [Providers and placement](#providers-and-placement)
- [Bid screening](#bid-screening)
- [Deprecated endpoints](#deprecated-endpoints)
- [Endpoints that do not exist](#endpoints-that-do-not-exist)

Secrets (`sealedSecrets`, `inheritSecretsFrom`, `ac-secret://` references) have their own file: **@secrets.md**. Logs, events, status and shell come from the provider: **@operations.md**.

## Deployments

### Create a deployment

```
POST /v1/deployments
```

**Body (`data`):**

| Field | Required | Description |
|---|---|---|
| `sdl` | yes | The SDL as a YAML string, at most 512 KiB |
| `name` | no | 1 to 256 characters, shown wherever the deployment is listed. Defaults to the SDL's service names joined with `+`. |
| `runtimeLimitHours` | no | 1 to 48. Console closes the deployment that many hours after its lease starts and returns the unspent credits. Omit for always-on funding. |
| `sealedSecrets` | no | A JWE carrying secret values the SDL references as `ac-secret://NAME`. See **@secrets.md**. |
| `inheritSecretsFrom` | no | Dseq of one of your deployments, open or closed, whose stored secrets this one starts from. See **@secrets.md**. |

Don't send `deposit`. Console funds every deployment from the account's credits and ignores the field.

**Example:**

```bash
SDL=$(cat deploy.yaml)
curl -sX POST https://console-api.akash.network/v1/deployments \
  -H "x-api-key: $AKASH_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -nc --arg sdl "$SDL" '{data: {sdl: $sdl, name: "web-prod"}}')"
```

**Response (201):**

```json
{
  "data": {
    "dseq": "1785245500842",
    "manifest": "<the manifest Console derived from the SDL>",
    "signTx": { "code": 0, "transactionHash": "...", "rawLog": "..." }
  }
}
```

Keep `dseq`. You don't need `manifest`: Console records the deployment's definition and sends the manifest to the provider itself when you create the lease.

**Errors:**

| Status | When |
|---|---|
| 400 | The SDL is invalid, or a secret reference has no value, or `sealedSecrets` is malformed, expired or names a value no service references |
| 402 | Not enough credit. `code` is `insufficient_balance` or `balance_top_up_pending` (see **@overview.md**). Free-trial refusals, such as a GPU model the trial excludes, answer `payment_required`. |
| 403 | `sealedSecrets` was sealed for another user or another SDL. Free-trial accounts also get 403 when the deployment exceeds the trial's resource limits, or `code: fair_use_policy_required` until the Fair Use Policy is accepted in the Console UI. |
| 404 | `inheritSecretsFrom` names no deployment of yours |
| 409 | The seal used a retired key (refetch `GET /v1/sdl-secrets-context` and seal again), or `code` is `inherited_secrets_unreadable` (permanent: supply the values in `sealedSecrets` instead) |
| 503 | The key service was briefly unreachable. Retry. |

### List deployments

```
GET /v1/deployments?state=active&skip=0&limit=100
```

| Query | Default | Description |
|---|---|---|
| `state` | `active` | `active` or `closed`. Closed deployments only appear with `state=closed`. |
| `search` | none | Case-insensitive substring of the deployment's name or dseq. `total` and `hasMore` then describe the matches. |
| `reverse` | `false` | `true` lists newest first; the default is oldest first |
| `skip` | `0` | Offset |
| `limit` | `100` | Page size, 1 to 100 |

**Response:**

```json
{
  "data": {
    "deployments": [
      {
        "deployment": { "id": { "owner": "akash1...", "dseq": "1785245500842" }, "state": "active", "created_at": "..." },
        "leases": [ ... ],
        "escrow_account": { ... },
        "name": "web-prod",
        "groups": [ ... ],
        "settings": { "name": "web-prod", "runtimeLimitHours": null, "runtimeEndsAt": null, "closed": false }
      }
    ],
    "pagination": { "total": 7, "skip": 0, "limit": 100, "hasMore": false }
  }
}
```

Page on `hasMore`, not on `total`: `total` comes from Console's index, can briefly lag, and is `null` when the index can't answer. Leases in this list carry no live `status`; read one deployment for that. A `search` over an account with more deployments than a search can span answers 422; page without `search` instead.

```bash
for STATE in active closed; do
  SKIP=0
  while :; do
    PAGE=$(curl -s "https://console-api.akash.network/v1/deployments?state=$STATE&skip=$SKIP&limit=100" \
      -H "x-api-key: $AKASH_API_KEY")
    echo "$PAGE" | jq -r '.data.deployments[] | "\(.deployment.id.dseq)\t\(.name // "-")\t\(.deployment.state)"'
    [ "$(echo "$PAGE" | jq -r '.data.pagination.hasMore')" = "true" ] || break
    SKIP=$((SKIP + 100))
  done
done
```

For names alone, `GET /v1/deployment-names?dseq=1&dseq=2` answers `{ "data": { "1": "web-prod", "2": null } }`.

### Get a deployment

```
GET /v1/deployments/{dseq}
```

**Response:**

```json
{
  "data": {
    "deployment": { "id": { "owner": "akash1...", "dseq": "1785245500842" }, "state": "active", "created_at": "..." },
    "leases": [
      {
        "id": { "owner": "akash1...", "dseq": "1785245500842", "gseq": 1, "oseq": 1, "provider": "akash1prov...", "bseq": 21 },
        "state": "active",
        "price": { "denom": "uact", "amount": "1.234" },
        "status": {
          "services": { "web": { "available": 1, "total": 1, "uris": ["abc123.ingress.provider.example"], "ready_replicas": 1 } },
          "forwarded_ports": { "api": [{ "host": "provider.example", "port": 8080, "externalPort": 31234 }] },
          "ips": {}
        }
      }
    ],
    "escrow_account": { "state": { "state": "open", "funds": [{ "denom": "uact", "amount": "..." }] } },
    "name": "web-prod",
    "consoleSettings": { "sdl": "version: \"2.0\"\n...", "manifestVersion": "..." }
  }
}
```

This is the canonical read for a running deployment:

- **Where the service is reachable.** A global expose with `as: 80` gets an HTTP hostname: `status.services.<svc>.uris[0]`. Any other global port gets a random public port: `status.forwarded_ports.<svc>[]` gives `host` and `externalPort`. Leased IPs appear under `status.ips`.
- **Health.** `status.services.<svc>.available` against `total`. `status` is `null` when Console couldn't reach the provider; poll again.
- **The stored definition.** `consoleSettings.sdl` is the SDL Console recorded, re-serialized, with secret values replaced by `ac-secret://` references. `consoleSettings.manifestVersion` is what `PATCH` takes as `ifManifestVersion`. Both are `null` for a deployment Console holds no definition for.
- **Reclamation.** A lease whose provider has flagged its capacity for reclamation carries `reclamation.deadline` (unix seconds). See `rules/sdl/reclamation.md`.
- **GPUs.** `offeredGpus` is what the provider bid with, which is what an "any model" request resolved to. `detectedGpus` is what Console observed inside the containers, with the driver version.

### Patch a deployment

```
PATCH /v1/deployments/{dseq}
```

Changes the definition Console stored, then sends the deployment update and the new manifest. The lease and the provider stay; the provider restarts the touched services. Only what you name changes, and the SDL itself is never part of the request.

**Body (`data`):**

| Field | Description |
|---|---|
| `services.<name>.image` | New image tag |
| `services.<name>.env` | Map of variable name to value, merged into the service's env. `null` removes a variable. |
| `services.<name>.command`, `.args` | Arrays of strings, or `null` to clear |
| `services.<name>.credentials` | Private registry `{ host, username, password }`, or `null` to clear. Always stored sealed. |
| `services.<name>.expose.<containerPort>` | Keyed by the container port the stored SDL declares: `port`, `as`, `accept` (replaces the custom-domain list), `httpOptions` (`maxBodySize`, `readTimeout`, `sendTimeout`, `nextTries`, `nextTimeout`, `nextCases`) |
| `services.<name>.storage.<volume>` | `mount` and `readOnly` only |
| `name` | Renames the deployment. On its own it sends no update and works even when Console holds no definition. |
| `sealedSecrets` | New values for the secret names this patch replaces; omitted names keep their stored values. See **@secrets.md**. |
| `ifManifestVersion` | Optimistic lock: the `manifestVersion` you read. Without it the patch still refuses to overwrite a concurrent one. |

```bash
curl -sX PATCH "https://console-api.akash.network/v1/deployments/$DSEQ" \
  -H "x-api-key: $AKASH_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "services": {
        "worker": {
          "image": "ghcr.io/acme/worker:3.0.1",
          "env": { "QUEUE_CONCURRENCY": "8", "LEGACY_MODE": null }
        }
      }
    }
  }'
```

The response is the deployment, plus the `manifestVersion` the patch recorded. Env values written by a patch without `sealedSecrets` are stored sealed: the container gets them, but `GET` shows `ac-secret://` references in their place. To keep plain values readable, send a seal of an empty map with the patch (**@secrets.md**).

**What a patch can't change.** Compute resources (CPU, memory, storage sizes, GPUs), replica counts, groups and placement, and the protocol, kind or number of exposed endpoints are fixed when the deployment is created. Asking for them answers 422 `deployment_resources_changed`, and nothing is sent. To resize, create a new deployment from the stored SDL (`consoleSettings.sdl`, edited), pass `inheritSecretsFrom: <old dseq>` so its secrets carry over, lease it, then close the old one. Moving a global port onto or off `as: 80` also changes the endpoint kind and is refused.

**Errors:**

| Status | `code` | When |
|---|---|---|
| 400 | | Names a service, port or volume the stored SDL doesn't declare, leaves a secret reference without a value, or moves a port in a way that is refused |
| 403 | | `sealedSecrets` was sealed for another user, or bound to an SDL other than the stored one |
| 404 | | Console holds no definition for this deployment; record one first (below) |
| 409 | `deployment_definition_changed` | Another patch landed first. Re-read, then re-send. A 409 without this code means the seal used a retired key. |
| 422 | `deployment_resources_changed` | The change needs a new deployment |
| 500 | `stored_secrets_unreadable`, `stored_sdl_unreadable` | The stored state is permanently unreadable; a retry won't help |
| 503 | | The key service was briefly unreachable. Retry. |

If the deployment update fails after the definition was recorded, re-send the identical request: it recomputes the same manifest version and finishes the update.

### Record a definition

```
POST /v1/deployments/{dseq}/definition
```

For a deployment Console holds no definition for (`consoleSettings` is `null`), such as one created before Console recorded definitions. Send `{ "data": { "sdl": "...", "sealedSecrets": "..." } }`. The SDL must produce exactly the manifest the deployment already runs, so nothing is sent to the provider; afterwards the deployment takes patches. Answers 201 with `{ sdl, manifestVersion }`, 409 `deployment_definition_exists` if a definition exists (patch instead), or 422 `deployment_definition_mismatch` if the SDL differs from what runs.

### Close a deployment

```
DELETE /v1/deployments/{dseq}
DELETE /v1/deployments/{dseq}?async=true
```

Closes the deployment and its leases. Whatever escrow is left returns to the account's available balance.

- Without `async`, the call returns `200 { "data": { "success": true } }` once the close went through.
- With `async=true`, Console checks the request, then answers `202 { "data": { "activityId": "<uuid>" } }` and finishes in the background. Poll `GET /v1/activities/{activityId}` until `status` is `succeeded` or `failed` (`meta.error` says why). The same call can still answer 200: when the deployment was already closed, or when background close isn't enabled for the account.

Closing an already-closed deployment is a no-op, so a retried close is safe.

```bash
RESP=$(curl -s -w '\n%{http_code}' -X DELETE "https://console-api.akash.network/v1/deployments/$DSEQ?async=true" \
  -H "x-api-key: $AKASH_API_KEY")
CODE=$(echo "$RESP" | tail -n1)
if [ "$CODE" = "202" ]; then
  ACTIVITY=$(echo "$RESP" | sed '$d' | jq -r .data.activityId)
  until STATUS=$(curl -s "https://console-api.akash.network/v1/activities/$ACTIVITY" \
      -H "x-api-key: $AKASH_API_KEY" | jq -r .data.status) && [ "$STATUS" != "pending" ]; do
    sleep 5
  done
  echo "close $STATUS"
fi
```

`GET /v1/activities` lists recent actions newest first (`limit` up to 100, `cursor`, `status`, `type=deployment_close`), with a `nextCursor` for the next page.

### Other deployment reads

| Endpoint | Auth | Returns |
|---|---|---|
| `GET /v1/deployment-names?dseq=…&dseq=…` | key | `{ data: { "<dseq>": name or null } }` |
| `GET /v1/weekly-cost` | key | `{ data: { weeklyCost } }`: USD per week across the account's running deployments |
| `GET /v1/deployment-funding-config` | public | The constants automatic funding runs on (see **@account-and-funding.md**) |
| `GET /v1/deployment/{owner}/{dseq}` | public | A read-only view of any deployment: monthly cost, provider, events. For your own, prefer `GET /v1/deployments/{dseq}`. |

## Leases

### Accept bids

```
POST /v1/leases
```

**Body: flat, not wrapped in `data`.**

```json
{
  "leases": [
    { "dseq": "1785245500842", "gseq": 1, "oseq": 1, "provider": "akash1providerA..." }
  ]
}
```

One call creates a lease per entry and sends each provider the manifest Console recorded at create. Copy `dseq`, `gseq`, `oseq` and `provider` from the bid's `bid.id`; leave out `owner` and `bseq`.

A deployment with several groups needs one entry per group, **all in the same call**. A second call for the same dseq finds the first call's lease, treats the request as a retry and creates nothing.

Don't send `manifest`. The field is deprecated, and Console only falls back to it for a deployment it holds no definition for (it answers 422 when it has neither).

```bash
BIDS=$(curl -s "https://console-api.akash.network/v1/bids?dseq=$DSEQ" -H "x-api-key: $AKASH_API_KEY")
CHEAPEST=$(echo "$BIDS" | jq -c '[.data[] | select(.bid.state == "open")] | sort_by(.bid.price.amount | tonumber) | .[0].bid.id')

curl -sX POST https://console-api.akash.network/v1/leases \
  -H "x-api-key: $AKASH_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -nc --argjson id "$CHEAPEST" '{leases: [{dseq: $id.dseq, gseq: $id.gseq, oseq: $id.oseq, provider: $id.provider}]}')"
```

The response is the deployment object. Lease status fills in once the provider starts the workload; poll `GET /v1/deployments/{dseq}`.

**Retries are safe.** If the leases already exist, the call skips creating them and only re-sends the manifest.

| Status | `code` | Meaning |
|---|---|---|
| 502 | `provider_unreachable` | The provider didn't answer. No lease was created; choose another bid. |
| 502 | `manifest_not_delivered` | The lease exists but the provider didn't take the manifest. Send the same request again, or close the deployment to stop paying for it. |
| 400 | | A bid is no longer open, or the body is malformed |

There is no endpoint to close a single lease, and none to read one: close the deployment, and read leases from `GET /v1/deployments/{dseq}`.

## Bids

```
GET /v1/bids?dseq={dseq}
```

Poll every few seconds after creating the deployment; bids usually arrive within 5 to 30 seconds, and `data` is `[]` until then. `GET /v1/bids/{dseq}` returns the same thing.

```json
{
  "data": [
    {
      "bid": {
        "id": { "owner": "akash1...", "dseq": "1785245500842", "gseq": 1, "oseq": 1, "provider": "akash1prov...", "bseq": 21 },
        "state": "open",
        "price": { "denom": "uact", "amount": "1.523" },
        "created_at": "...",
        "resources_offer": [ { "resources": { "cpu": { "units": { "val": "500" } }, "gpu": { "units": { "val": "0" } } }, "count": 1 } ],
        "reclamation_window": "3600s"
      },
      "escrow_account": { ... }
    }
  ]
}
```

- `price.amount` is `uact` per block, as a decimal string. Compare with `tonumber`.
- Only `state: "open"` bids can be accepted.
- `resources_offer` is what the provider committed to; check it before accepting a GPU bid.
- `reclamation_window` is present when the provider may reclaim capacity with that much notice. See `rules/sdl/reclamation.md`.

No bids after a minute usually means no provider matches the SDL or the price is too low. Run the matcher in `rules/bid-matching/`.

## Runtime limits (deployment settings v2)

Automatic funding is always on. What these endpoints control is the **runtime limit**: an optional cap after which Console closes the deployment and returns the unspent credits.

```
GET   /v2/deployment-settings/{dseq}
PATCH /v2/deployment-settings/{dseq}
POST  /v2/deployment-settings
```

`GET` returns `runtimeLimitHours` (`null` for always-on), `runtimeEndsAt` (`null` until the lease starts), `sdl`, and the funding estimate fields (`estimatedTopUpAmount`, `topUpFrequencyMs`). A deployment created through `POST /v1/deployments` already has its settings row. One that answers 404 (an older deployment) gets one from `POST /v2/deployment-settings` with `{ "data": { "dseq": "..." } }`.

```bash
curl -sX PATCH "https://console-api.akash.network/v2/deployment-settings/$DSEQ" \
  -H "x-api-key: $AKASH_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"data": {"runtimeLimitHours": 96}}'
```

- Send the new **total**, not an increment. A limit can be raised by at most 48 hours per request, up to 8760; a deployment without a limit can be given one of at most 48.
- Lowering a limit is not supported. Send `null` to drop it and return to always-on funding.
- `closeReason` (`no_longer_needed`, `cost_or_budget`, `migrating_elsewhere`, `performance_or_reliability`, `testing_or_project_complete`, `other`) and `closeReasonDetails` record why a deployment was closed. They can't be sent together with `runtimeLimitHours`.
- 409 means another change to the limit landed first; re-read and retry.

`autoTopUpEnabled` is accepted for backwards compatibility and an explicit `false` is rejected. The older `/v1/deployment-settings/*` paths are UI-internal.

## Providers and placement

All public, no key needed.

| Endpoint | Returns |
|---|---|
| `GET /v1/providers` | Every provider, offline ones included, as a bare array. Filter on `isOnline` and `isAudited`. `?addresses=a,b` narrows it; `?scope=trial` lists providers a free-trial account can lease from. |
| `GET /v1/providers/{address}` | One provider: `hostUri`, `attributes`, `isOnline`, `isAudited`, uptime, `stats` (capacity), `gpuModels`, `reclamationWindow` (seconds of notice before reclaiming capacity, or `null`), `gpuDrivers` (NVIDIA driver and CUDA versions Console confirmed on its leases), `reportedCpuArchs` |
| `GET /v1/provider-search` | Providers filtered and paged: `search`, `online`, `audited`, `regions`, `gpu`, `gpuModels`, `sort`, `skip`, `limit` (≤100). Answers `{ data: { providers, pagination } }`. |
| `GET /v1/placement-options` | Regions with audited online providers (`regions`, `regionProviderCounts`) and the GPUs they can serve right now: per model, `providerCount`, `availableUnits`, `maxNodeFreeUnits`, and the memory/interface variants providers would bid on |
| `GET /v1/provider-regions`, `/v1/provider-attributes-schema`, `/v1/auditors` | Placement-attribute vocabularies for SDL editors |

`GET /v1/providers/{address}` is where the provider's `hostUri` comes from for logs and shell. It is the object itself: `.hostUri`, not `.data.hostUri`.

Check `GET /v1/placement-options` before writing a GPU SDL: a model with `providerCount: 0` gets no bids, and a replica asking for more GPUs than `maxNodeFreeUnits` can't fit on one node.

## Bid screening

```
POST /v1/bid-screening
```

Public. Predicts which providers would bid on a group without creating anything. **Body: flat**, with resources in their on-chain form (what `GET /v1/deployments/{dseq}` returns under `groups[].group_spec`):

```json
{
  "requirements": { "signedBy": { "allOf": [], "anyOf": [] }, "attributes": [] },
  "resources": [
    {
      "resource": {
        "id": 1,
        "cpu": { "units": { "val": "500" } },
        "memory": { "quantity": { "val": "536870912" } },
        "gpu": { "units": { "val": "0" } },
        "storage": [{ "name": "default", "quantity": { "val": "1073741824" } }]
      },
      "count": 1,
      "price": { "denom": "uact", "amount": "1000" }
    }
  ],
  "timezone": "UTC"
}
```

CPU is in millicores, memory and storage in bytes, all as strings. `timezone` is required (an IANA zone; it buckets the incident history). `reclamationWindow` (seconds) keeps only providers that give at least that much notice.

**Response:** `{ "providers": [{ "owner", "hostUri", "isAudited", "location", "organization", "availableGpus", "incidents": [...] }] }`.

From an SDL file, the matcher in `rules/bid-matching/` is simpler: it reads the SDL directly and reports why providers drop out.

## Deprecated endpoints

### Full-SDL update

```
PUT /v1/deployments/{dseq}
```

Deprecated in favor of `PATCH` and scheduled for removal. It resubmits the whole SDL, so every secret value has to be resupplied, and it refuses resource changes with the same 422 `deployment_resources_changed`. Don't generate new code for it.

### Deposit

```
POST /v1/deposit-deployment
```

Deprecated and scheduled for removal. Console tops every deployment up automatically while the account has credits, so there is nothing for it to do. If an account runs low, the fix is adding credits in the Console UI. See [How Funding Works](https://akash.network/docs/getting-started/how-funding-works/).

## Endpoints that do not exist

Older docs, and models trained on them, invent these. None exist:

| Invented | Use |
|---|---|
| `POST /deployment`, `GET /deployment/{dseq}`, `DELETE /deployment/{dseq}` | `/v1/deployments`, `/v1/deployments/{dseq}` |
| `POST /deployment/{dseq}/deposit`, `POST /wallet/deposit` | Nothing: funding is automatic; credits are added in the Console UI |
| `POST /lease` (single), `GET` or `DELETE /lease/{dseq}/{gseq}/{oseq}` | `POST /v1/leases` (batch); read leases from `GET /v1/deployments/{dseq}`; close the deployment |
| `GET /providers/{address}/status` | `GET /v1/providers/{address}` |
| `POST /sdl/validate`, `POST /v1/sdl/validate` | Validate client-side; `POST /v1/deployments` answers 400 for an invalid SDL |
| `POST /sdl/price` | No pricing endpoint. Prices come from bids (`GET /v1/bids?dseq=`). |
| `POST /wallet/create` | Accounts are created in the Console UI |
| `GET /wallet/balance` | `GET /v1/balances` |
| `POST /v1/auth/refresh` | Re-mint with `POST /v1/create-jwt-token` |
| `console-api.akash.network/v1/proxy/...`, `/v1/logs/...` | Logs come from the provider (**@operations.md**) |
