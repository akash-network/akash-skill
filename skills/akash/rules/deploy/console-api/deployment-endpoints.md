# Console API — Deployment Endpoint Reference

Every endpoint below lives under `https://console-api.akash.network` and takes `x-api-key: <key>` unless marked public. Write endpoints wrap the body in `{ "data": { ... } }`; the exceptions are called out. The error envelope and the cross-cutting error codes are in **@overview.md**.

## Quick links

- [Deployments](#deployments): create (from an SDL, or [without one](#create-a-deployment-without-an-sdl)), list, read, patch, close, move between projects
- [Definitions](#definitions): [check one](#check-a-definition), [replace one whole](#replace-a-whole-definition), [record one](#record-a-definition), [list a deployment's secrets](#list-a-deployments-secrets)
- [Leases](#leases)
- [Bids](#bids)
- [Runtime limits](#runtime-limits-deployment-settings-v2)
- [Providers and placement](#providers-and-placement)
- [Bid screening](#bid-screening)
- [Deprecated endpoints](#deprecated-endpoints)
- [Endpoints that do not exist](#endpoints-that-do-not-exist)

Secrets (`secretEnv`, `sealedSecrets`, `inheritSecretsFrom`, `ac-secret://` references) have their own file: **@secrets.md**. Logs, events, status and shell come from the provider: **@operations.md**.

## Deployments

### Create a deployment

```
POST /v1/deployments
```

**Body (`data`):**

| Field | Required | Description |
|---|---|---|
| `sdl` | one of `sdl`, `definition`, `service`, `templateId` | The SDL as a YAML string, at most 512 KiB |
| `definition` | one of | The same SDL as a JSON object (`version`, `services`, `profiles`, `deployment`, `endpoints`). See [Definitions as JSON](#definitions-as-json). |
| `service` | one of | An image, resources, ports and env, from which Console writes the SDL. See [Create a deployment without an SDL](#create-a-deployment-without-an-sdl). |
| `templateId` | one of | Without `sdl` or `definition`: the gallery template to deploy, with `overrides` applied. With either: only records which template the document came from. |
| `overrides` | no | Changes to the template's SDL, keyed by service name. Only with `templateId` and no `sdl` or `definition`. |
| `name` | no | 1 to 256 characters, shown wherever the deployment is listed. Defaults to the SDL's service names joined with `+`. |
| `runtimeLimitHours` | no | 1 to 48. Console closes the deployment that many hours after its lease starts and returns the unspent credits. Omit for always-on funding. |
| `secretEnv` | no | Names of the env variables whose values are secret, such as `["API_KEY"]`. Console encrypts those and stores every other env value readable; `[]` keeps all of them readable. Needs no encryption on your side. Without it, and without `sealedSecrets`, every env value is encrypted. See **@secrets.md**. |
| `sealedSecrets` | no | A JWE carrying secret values the SDL references as `ac-secret://NAME`. See **@secrets.md**. |
| `inheritSecretsFrom` | no | Dseq of a deployment you can change in the same account or team, open or closed, whose stored secrets this one starts from. See **@secrets.md**. |
| `projectId` | no | The project to file the deployment in. Without it: the key's project for a key bound to one, otherwise the default project, and 400 `project_required` when the caller can't deploy there. See **@teams-and-projects.md**. |

There is no deposit to send. Console funds every deployment from the credits of the key's account or team, and the deprecated `deposit` field is being removed: leave it out.

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
| 400 | The SDL is invalid (`POST /v1/deployments/validate` lists every problem at once, see [Check a definition](#check-a-definition)), or a secret reference has no value, or `secretEnv` names a variable no service sets, or `sealedSecrets` is malformed, expired or names a value no service references. `code: project_required`: no project could be chosen, so pass `projectId`. |
| 402 | Not enough credit. `code` is `insufficient_balance` or `balance_top_up_pending` (see **@overview.md**). Free-trial refusals, such as a GPU model the trial excludes, answer `payment_required`. |
| 403 | `sealedSecrets` was sealed for another user or another SDL. Free-trial accounts also get 403 when the deployment exceeds the trial's resource limits, or `code: fair_use_policy_required` until the Fair Use Policy is accepted in the Console UI. `code: project_budget_exceeded`: the project's monthly budget is spent. A team `viewer` or `billing` member's key can't deploy at all. |
| 404 | `inheritSecretsFrom` names no deployment you can change, or `projectId` names a project you can't deploy into |
| 409 | The seal used a retired key (refetch `GET /v1/sdl-secrets-context` and seal again), or `code` is `inherited_secrets_unreadable` (permanent: supply the values in `sealedSecrets` instead) |
| 503 | The key service was briefly unreachable. Retry. |

### Create a deployment without an SDL

The same `POST /v1/deployments` takes simple inputs in place of `sdl`. Console writes the SDL and records it, so the deployment then behaves like any other: its SDL shows on the Update tab and in `consoleSettings.sdl`, `PATCH` changes it, and a redeploy starts from it. Bids, the lease, and everything after are the same calls.

Send exactly one of `sdl`, `definition`, `service`, or `templateId` without a document.

**From an image (`data.service`).** One service, which Console names `app`:

| Field | Required | Description |
|---|---|---|
| `service.image` | yes | Container image with its tag, such as `ghcr.io/acme/api:1.4.0` |
| `service.resources.cpu` | yes | CPU units; `0.5` is half a core |
| `service.resources.memory` | yes | A number and a unit, such as `512Mi`. Units: `k`, `Ki`, `M`, `Mi`, `G`, `Gi`, `T`, `Ti`. |
| `service.resources.storage` | yes | Ephemeral disk, written the same way, such as `1Gi` |
| `service.resources.gpu` | no | `{ "units": 1, "model": "rtx4090" }`. NVIDIA only; leave `model` out to take any NVIDIA GPU. |
| `service.ports` | yes | At least one `{ "port": 3000, "as": 80 }`. `port` is the container port; `as` is the port it is reached on and defaults to `port`. Every port is public. A port reached on 80 gets a hostname from the provider; any other is reached on the provider's host through a port the provider picks. |
| `service.env` | no | Map of variable name to value. `secretEnv` says which values are secret, exactly as it does for an SDL. |

```bash
curl -sX POST https://console-api.akash.network/v1/deployments \
  -H "x-api-key: $AKASH_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "name": "api-prod",
      "service": {
        "image": "ghcr.io/acme/api:1.4.0",
        "resources": { "cpu": 1, "memory": "1Gi", "storage": "2Gi" },
        "ports": [{ "port": 3000, "as": 80 }],
        "env": { "LOG_LEVEL": "info", "API_KEY": "<INSERT_SECRET>" }
      },
      "secretEnv": ["API_KEY"]
    }
  }'
```

The SDL Console writes has one replica, the Console's default price ceiling, and no placement requirements. Patch the service as `app`, for example `{"data": {"services": {"app": {"image": "ghcr.io/acme/api:1.4.1"}}}}`. Write an SDL instead when the workload needs more than one service, more than one replica, persistent storage, a private port, a start command, or private registry credentials.

**From a gallery template (`data.templateId` without `sdl`).** Console deploys the template's own SDL. `GET /v1/templates-list` (public, no key) lists the gallery by category, with each template's `id`; `GET /v1/templates/{id}` returns its SDL in `data.deploy`, which shows the service names. `data.overrides` changes that SDL before it is deployed. It is keyed by service name and takes the same fields as `services` in `PATCH /v1/deployments/{dseq}` (`image`, `env`, `command`, `args`, `credentials`, `expose`, `storage`), with the same limits: no resource, replica or placement changes.

```bash
curl -sX POST https://console-api.akash.network/v1/deployments \
  -H "x-api-key: $AKASH_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "templateId": "<template id from /v1/templates-list>",
      "overrides": {
        "<service name>": { "env": { "LOG_LEVEL": "debug", "API_KEY": "<INSERT_SECRET>" } }
      },
      "secretEnv": ["API_KEY"]
    }
  }'
```

`templateId` sent together with `sdl` or `definition` keeps its older meaning: it only records which template the SDL came from, and `overrides` is refused.

**Errors**, on top of the ones above:

| Status | When |
|---|---|
| 400 | The request names no source or more than one (`Send one of sdl, service or templateId`, `Send either sdl or service, not both`), `service` is combined with `templateId`, `overrides` is sent with `sdl` or without `templateId`, a `service` field is missing or malformed (no port, a port listed twice, a size without a unit), or `overrides` names a service, port or volume the template does not declare, or moves a port in a way `PATCH` refuses |
| 404 | `templateId` without `sdl` names a template the gallery does not list |

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
| `projectId` | none | Only the deployments filed in this project. A project you can't reach lists nothing. |

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
        "projectId": "3f0c...",
        "groups": [ ... ],
        "settings": { "name": "web-prod", "runtimeLimitHours": null, "runtimeEndsAt": null, "closed": false }
      }
    ],
    "pagination": { "total": 7, "skip": 0, "limit": 100, "hasMore": false }
  }
}
```

Page on `hasMore`, not on `total`: `total` comes from Console's index, can briefly lag, and is `null` when the index can't answer. Leases in this list carry no live `status`; read one deployment for that. A `search` over an account with more deployments than a search can span answers 422; page without `search` instead. In a team, the list covers the projects the key reaches, each deployment carries its `projectId`, and a team with more open deployments than one list can check answers 422 too: filter with `projectId`.

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
    "consoleSettings": {
      "sdl": "version: \"2.0\"\n...",
      "definition": { "version": "2.0", "services": { ... }, "profiles": { ... }, "deployment": { ... } },
      "manifestVersion": "...",
      "templateId": null
    }
  }
}
```

This is the canonical read for a running deployment:

- **Where the service is reachable.** A global expose with `as: 80` gets an HTTP hostname: `status.services.<svc>.uris[0]`. Any other global port gets a random public port: `status.forwarded_ports.<svc>[]` gives `host` and `externalPort`. Leased IPs appear under `status.ips`.
- **Health.** `status.services.<svc>.available` against `total`. `status` is `null` when Console couldn't reach the provider; poll again.
- **The stored definition.** `consoleSettings.sdl` is the SDL Console recorded, re-serialized, with secret values replaced by `ac-secret://` references. `consoleSettings.definition` is the same document as JSON, ready to edit and send back to `PUT /v1/deployments/{dseq}/definition`. `consoleSettings.manifestVersion` is what `PATCH` and that `PUT` take as `ifManifestVersion`. `consoleSettings` is `null` for a deployment Console holds no definition for.
- **Reclamation.** A lease whose provider has flagged its capacity for reclamation carries `reclamation.deadline` (unix seconds). See `rules/sdl/reclamation.md`.
- **GPUs.** `offeredGpus` is what the provider bid with, which is what an "any model" request resolved to. `detectedGpus` is what Console observed inside the containers, with the driver version.

A deployment outside the projects the key reaches answers 404, as if it didn't exist.

### Patch a deployment

```
PATCH /v1/deployments/{dseq}
```

Changes the definition Console stored, then sends the deployment update and the new manifest. The lease and the provider stay; the provider restarts the touched services. Only what you name changes, and the SDL itself is never part of the request. To send a whole edited document instead, use [`PUT /v1/deployments/{dseq}/definition`](#replace-a-whole-definition).

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
| `secretEnv` | Names of the env variables this patch writes whose values are secret. Console encrypts those and stores the other written values readable; `[]` keeps all of them readable. See **@secrets.md**. |
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

The response is the deployment, plus the `manifestVersion` the patch recorded. Env values written by a patch that carries neither `secretEnv` nor `sealedSecrets` are stored encrypted: the container gets them, but `GET` shows `ac-secret://` references in their place. To keep plain values readable, send `secretEnv` with the patch: the names of the written variables that are secret, or `[]` when none is (**@secrets.md**).

**What a patch can't change.** Compute resources (CPU, memory, storage sizes, GPUs), replica counts, groups and placement, and the protocol, kind or number of exposed endpoints are fixed when the deployment is created. Asking for them answers 422 `deployment_resources_changed`, and nothing is sent. To resize, create a new deployment from the stored SDL (`consoleSettings.sdl`, edited), pass `inheritSecretsFrom: <old dseq>` so its secrets carry over, lease it, then close the old one. Moving a global port onto or off `as: 80` also changes the endpoint kind and is refused.

**Errors:**

| Status | `code` | When |
|---|---|---|
| 400 | | Names a service, port or volume the stored SDL doesn't declare, leaves a secret reference without a value, names a variable in `secretEnv` it doesn't write, or moves a port in a way that is refused |
| 403 | | `sealedSecrets` was sealed for another user, or bound to an SDL other than the stored one |
| 403 | `project_forbidden` | The deployment is filed in a project the key can't change |
| 404 | | Console holds no definition for this deployment; [record one](#record-a-definition) first |
| 409 | `deployment_definition_changed` | Another change landed first. Re-read, then re-send. A 409 without this code means the seal used a retired key. |
| 422 | `deployment_resources_changed` | The change needs a new deployment |
| 500 | `stored_secrets_unreadable`, `stored_sdl_unreadable` | The stored state is permanently unreadable; a retry won't help. Recover with the full SDL and every secret value on the deprecated [`PUT /v1/deployments/{dseq}`](#full-sdl-update). |
| 503 | | The key service was briefly unreachable. Retry. |

If the deployment update fails after the definition was recorded, re-send the identical request: it recomputes the same manifest version and finishes the update.

### Close a deployment

```
DELETE /v1/deployments/{dseq}
DELETE /v1/deployments/{dseq}?async=true
```

Closes the deployment and its leases. Whatever escrow is left returns to the account's available balance.

- Without `async`, the call returns `200 { "data": { "success": true } }` once the close went through.
- With `async=true`, Console checks the request, then answers `202 { "data": { "activityId": "<uuid>" } }` and finishes in the background. Poll `GET /v1/activities/{activityId}` until `status` is `succeeded` or `failed` (`meta.error` says why). The same call can still answer 200: when the deployment was already closed, or when background close isn't enabled for the account.

Closing an already-closed deployment is a no-op, so a retried close is safe. A deployment filed in a project the key can't change answers 403 `project_forbidden`.

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

### Move a deployment to another project

```
PATCH /v1/deployments/{dseq}/project
```

```bash
curl -sX PATCH "https://console-api.akash.network/v1/deployments/$DSEQ/project" \
  -H "x-api-key: $AKASH_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -nc --arg project "$TARGET_PROJECT_ID" '{data: {projectId: $project}}')"
```

Refiles the deployment in another project of the same account or team and answers `{ "data": { "dseq", "projectId" } }`. Nothing changes on chain: the lease, the provider and the escrow stay. Only team owners and admins may move (403 otherwise), and 404 means the deployment or the project is out of the key's reach. See **@teams-and-projects.md**.

### Other deployment reads

| Endpoint | Auth | Returns |
|---|---|---|
| `GET /v1/deployment-names?dseq=…&dseq=…` | key | `{ data: { "<dseq>": name or null } }` |
| `GET /v1/deployment-locations/{dseq}` | key | `{ data: { organizationId, organizationSlug, projectId } }`: where the deployment is filed, within the key's reach |
| `GET /v1/weekly-cost` | key | `{ data: { weeklyCost } }`: USD per week across the running deployments of the key's account or team |
| `GET /v1/deployment-funding-config` | public | The constants automatic funding runs on (see **@account-and-funding.md**) |
| `GET /v1/deployment/{owner}/{dseq}` | public | A read-only view of any deployment: monthly cost, provider, events. For your own, prefer `GET /v1/deployments/{dseq}`. |

## Definitions

Console records each deployment's SDL, its definition. `PATCH` changes named fields of it; the routes below check, replace or record the whole document, and list the secrets it references.

### Definitions as JSON

Wherever a request takes `sdl` (create, check, replace, record), it also takes `definition`: the same document as a JSON object, with the fields an SDL has (`version`, `services`, `profiles`, `deployment` and, where used, `endpoints`). Send exactly one of the two; both or neither answers 400. `GET /v1/deployments/{dseq}` returns the stored one in `consoleSettings.definition`, so a script can edit it with `jq` and send it back without touching YAML.

```json
{
  "data": {
    "definition": {
      "version": "2.0",
      "services": {
        "gateway": {
          "image": "ghcr.io/acme/gateway:1.9.0",
          "env": ["LOG_LEVEL=info", "DATABASE_URL=ac-secret://DATABASE_URL"],
          "expose": [{ "port": 8080, "as": 80, "to": [{ "global": true }] }]
        }
      },
      "profiles": {
        "compute": { "gateway": { "resources": { "cpu": { "units": 1 }, "memory": { "size": "1Gi" }, "storage": [{ "size": "2Gi" }] } } },
        "placement": { "dcloud": { "pricing": { "gateway": { "denom": "uact", "amount": 1000 } } } }
      },
      "deployment": { "gateway": { "dcloud": { "profile": "gateway", "count": 1 } } }
    }
  }
}
```

- Env entries stay `NAME=value` strings, as in YAML.
- At most 512 KiB once serialized as compact JSON, like `sdl`.
- A `sealedSecrets` sent beside a `definition` is bound to its compact JSON: `sdlHash` is the hash of `JSON.stringify(definition)`, keys in the order sent (**@secrets.md**).

### Check a definition

```
POST /v1/deployments/validate
POST /v1/deployments/{dseq}/definition/validate
```

Runs the checks the real request would run on a document and its secrets, and reports every error at once. Nothing is created, recorded, sealed or sent. The first previews `POST /v1/deployments`; the second previews `PUT /v1/deployments/{dseq}/definition` against that deployment, so it also catches changes only a new deployment can take and secret references the deployment can't fill.

**Body (`data`):** `sdl` or `definition`, plus the `sealedSecrets` and `secretEnv` the real request would carry. The create check also takes `inheritSecretsFrom`.

```bash
curl -sX POST https://console-api.akash.network/v1/deployments/validate \
  -H "x-api-key: $AKASH_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -nc --rawfile sdl deploy.yaml '{data: {sdl: $sdl}}')" \
  | jq '.data'
```

**Response (200):**

```json
{
  "data": {
    "valid": false,
    "errors": [
      { "path": "/services/gateway/env/1", "keyword": "sdl-reference", "message": "..." },
      { "path": "/services/worker", "keyword": "required", "message": "..." }
    ],
    "keptSecrets": []
  }
}
```

- **An invalid document still answers 200.** Read `valid` and `errors`, not the status.
- `path` is a JSON pointer into the document (empty when the error concerns the whole document). `keyword` names the failed check, such as `required`, `sdl-reference`, `secretEnv`, `maxLength` or `deployment_resources_changed`. `message` is for humans.
- `keptSecrets` lists the references whose value would come from what Console already stores (the deployment's own secrets, or those of `inheritSecretsFrom`) instead of from the request.
- It checks the document and its secrets only. Credits, projects and bids aren't part of it, so a valid create can still answer 402 or get no bids.

An error status means the check itself couldn't run:

| Status | When |
|---|---|
| 400 | Neither or both of `sdl` and `definition`, or a malformed, tampered or expired `sealedSecrets` |
| 403 | The seal was made for another user or another document. `project_forbidden` on the deployment check. |
| 404 | The deployment check: Console holds no definition for that dseq. The create check: `inheritSecretsFrom` names no deployment you can change. |
| 409 | The seal used a retired key (reseal), or `inherited_secrets_unreadable`. On the deployment check, `stored_secrets_unavailable` (see [Replace a whole definition](#replace-a-whole-definition)). |
| 500 | The deployment's stored SDL or secrets can't be read; permanent |
| 503 | The key service was briefly unreachable. Retry. |

### Replace a whole definition

```
PUT /v1/deployments/{dseq}/definition
```

Replaces the stored SDL with the one sent, then sends the deployment update and the new manifest, as `PATCH` does. Use it when the change is easier to express as an edited document than as named fields, such as an SDL kept in a repository. Stored secrets carry over: leave `NAME=ac-secret://NAME` wherever a secret stands, and its stored value is kept without being sent again. The same things are fixed as for a patch: groups, compute resources, replica counts and globally exposed ports.

**Body (`data`):**

| Field | Description |
|---|---|
| `sdl` or `definition` | The whole document: `consoleSettings.sdl` or `consoleSettings.definition`, edited |
| `secretEnv` | Names of the env variables whose values are secret. Applies to the values this request adds or changes. |
| `sealedSecrets` | A JWE holding only the secrets this request sets, bound to the document in this request (**@secrets.md**). Names left out keep their stored values. |
| `ifManifestVersion` | The `consoleSettings.manifestVersion` you read. 409 if the deployment moved on since. |
| `name` | Renames the deployment; left out, the name stays |

**What happens to each value:**

| In the document sent | Stored afterwards |
|---|---|
| `ac-secret://NAME` with no value in `sealedSecrets` | The stored value, kept |
| `ac-secret://NAME` with a value in `sealedSecrets` | The new value |
| A plain value, unchanged from one stored readable | Still readable |
| A plain value, added or changed, and the request carries neither `secretEnv` nor `sealedSecrets` | Encrypted |
| A plain value, added or changed, not named in a `secretEnv` (`[]` names none) | Readable |
| A plain value named in `secretEnv` | Encrypted, even if it was readable before |
| A stored secret no reference names any longer | Dropped |

Read, edit and send back:

```bash
API=https://console-api.akash.network
CURRENT=$(curl -s "$API/v1/deployments/$DSEQ" -H "x-api-key: $AKASH_API_KEY")

curl -sX PUT "$API/v1/deployments/$DSEQ/definition" \
  -H "x-api-key: $AKASH_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(echo "$CURRENT" | jq -c '{data: {
        definition: (.data.consoleSettings.definition
          | .services.gateway.image = "ghcr.io/acme/gateway:1.10.0"
          | .services.gateway.env += ["FEATURE_FLAGS=search"]),
        ifManifestVersion: .data.consoleSettings.manifestVersion,
        secretEnv: []
      }}')"
```

The response is the deployment plus the `manifestVersion` it recorded. With `?async=true` it answers 202 `{ "data": { "activityId", "manifestVersion" } }` once the definition is saved and applies it in the background; poll `GET /v1/activities/{activityId}`. A refusal answers on the request either way and saves nothing. Re-sending an identical request is safe: it recomputes the same version and finishes the update.

To see the outcome first, send the same `sdl` or `definition`, `secretEnv` and `sealedSecrets` to `POST /v1/deployments/{dseq}/definition/validate`: its `keptSecrets` lists the stored values that would be kept.

**Errors:**

| Status | `code` | When |
|---|---|---|
| 400 | | Invalid SDL; a reference with neither a value in `sealedSecrets` nor a stored one; a sealed name no service references; a `secretEnv` name no service sets; a malformed seal; both or neither of `sdl` and `definition` |
| 403 | | The seal was made for another user or another document. A seal bound to the stored SDL instead of the one sent is refused too. |
| 403 | `project_forbidden` | The deployment is filed in a project the key can't change |
| 404 | | Console holds no definition for this deployment; [record one](#record-a-definition) first |
| 409 | `deployment_definition_changed` | The deployment changed since `ifManifestVersion`, or during the request. Re-read, then re-send. A 409 without a code means the seal used a retired key: reseal. |
| 409 | `stored_secrets_unavailable` | In a team, the stored secrets were sealed for a member who has since deleted their account. Send the replace again with a value for every `ac-secret://` reference it makes; Console then stores them in place of the old ones. A replace that still relies on a stored value, and `PATCH`, keep failing. |
| 422 | `deployment_resources_changed` | The change needs a new deployment; nothing was recorded |
| 500 | `stored_secrets_unreadable`, `stored_sdl_unreadable` | The stored state is permanently unreadable; a retry won't help. Recover with the full SDL and every secret value on the deprecated [`PUT /v1/deployments/{dseq}`](#full-sdl-update). |
| 503 | | The key service was briefly unreachable. Retry. |

### Record a definition

```
POST /v1/deployments/{dseq}/definition
```

For a deployment Console holds no definition for (`consoleSettings` is `null`), such as one created before Console recorded definitions or outside Console. Send `{ "data": { "sdl": "..." } }` or `{ "data": { "definition": { ... } } }`, with `sealedSecrets` for its `ac-secret://` references. The document must produce exactly the manifest the deployment already runs, so nothing is sent to the provider, and a closed deployment can be recorded too. Afterwards the deployment takes patches and replacements like any other.

- There is no `secretEnv` here. Without `sealedSecrets`, every env value is stored encrypted, as on a create that says nothing about secrets; with one, the plain values are stored readable.
- Answers 201 with `{ "data": { "sdl", "manifestVersion" } }`.
- 409 `deployment_definition_exists`: Console already holds a definition, which this route never overwrites. Patch or replace it instead.
- 422 `deployment_definition_mismatch`: the document differs from what runs; nothing was recorded. Record what runs, then replace it.
- 404: no deployment of yours has this dseq. 503: retry.

### List a deployment's secrets

```
GET /v1/deployments/{dseq}/secrets
```

```bash
curl -s "https://console-api.akash.network/v1/deployments/$DSEQ/secrets" \
  -H "x-api-key: $AKASH_API_KEY" | jq '.data.secrets'
```

```json
{
  "data": {
    "secrets": [
      { "name": "REGISTRY_PASSWORD", "usedBy": [{ "service": "gateway", "credential": "password" }] },
      { "name": "SIGNING_KEY", "usedBy": [{ "service": "gateway", "env": "SIGNING_KEY" }, { "service": "worker", "env": "JWT_SIGNING_KEY" }] },
      { "name": "s0_e2", "usedBy": [{ "service": "gateway", "env": "DATABASE_URL" }] }
    ]
  }
}
```

Each secret the stored SDL references, once, sorted by name, with every env variable (`env`) or registry credential half (`credential`: `username` or `password`) it fills. **Values are never returned**; the list is read from the stored SDL and decrypts nothing. Names like `s0_e2` are ones Console chose when it encrypted a plain value for you (through `secretEnv`, or by default). Use the names to rotate a value with `sealedSecrets` on `PATCH`, or to know which references a replacement keeps.

404 means Console holds no definition for the deployment, or no deployment you can read has this dseq; the two are deliberately indistinguishable. 500 `stored_sdl_unreadable` is permanent.

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
| 403 | `project_forbidden` | The deployment is filed in a project the key can't change |
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

Deprecated and scheduled for removal. It resubmits the whole SDL and every secret value with it, and refuses resource changes with the same 422 `deployment_resources_changed`. Don't generate new code for it: use `PATCH` to change named fields, or [`PUT /v1/deployments/{dseq}/definition`](#replace-a-whole-definition) to send a whole SDL while keeping the stored secrets. The one exception: it never reads the stored SDL or secrets, so it is for now the only way out of `stored_secrets_unreadable` or `stored_sdl_unreadable`, by sending the full SDL with every secret value. For `stored_secrets_unavailable`, use [`PUT /v1/deployments/{dseq}/definition`](#replace-a-whole-definition) with every secret value instead.

### Deposit

```
POST /v1/deposit-deployment
```

Deprecated and being removed. Don't call it, and don't send `deposit` on create: Console funds every deployment from the account's credits and tops it up automatically while credits last. To keep deployments running, keep credits available: the user adds credits in the Console UI under **Billing**, or turns on **Auto recharge** there so the card is charged before credits run out (**@account-and-funding.md**).

## Endpoints that do not exist

Older docs, and models trained on them, invent these. None exist:

| Invented | Use |
|---|---|
| `POST /deployment`, `GET /deployment/{dseq}`, `DELETE /deployment/{dseq}` | `/v1/deployments`, `/v1/deployments/{dseq}` |
| `POST /deployment/{dseq}/deposit`, `POST /wallet/deposit` | Nothing: funding is automatic; credits are added in the Console UI |
| `POST /lease` (single), `GET` or `DELETE /lease/{dseq}/{gseq}/{oseq}` | `POST /v1/leases` (batch); read leases from `GET /v1/deployments/{dseq}`; close the deployment |
| `GET /providers/{address}/status` | `GET /v1/providers/{address}` |
| `POST /sdl/validate`, `POST /v1/sdl/validate` | `POST /v1/deployments/validate` ([Check a definition](#check-a-definition)) |
| `POST /sdl/price` | No pricing endpoint. Prices come from bids (`GET /v1/bids?dseq=`). |
| `POST /wallet/create` | Accounts are created in the Console UI |
| `GET /wallet/balance` | `GET /v1/balances` |
| `POST /v1/auth/refresh` | Re-mint with `POST /v1/create-jwt-token` |
| `console-api.akash.network/v1/proxy/...`, `/v1/logs/...` | Logs come from the provider (**@operations.md**) |
