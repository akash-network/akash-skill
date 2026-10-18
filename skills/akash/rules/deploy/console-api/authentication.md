# Console API Authentication

| Credential | Header | Use |
|---|---|---|
| **API key** | `x-api-key: <key>` | Everything a script, CI job or backend does |
| Console session JWT | `Authorization: Bearer <jwt>` | The Console web app's login session. Scripts don't use it. |
| Provider JWT | `Authorization: Bearer <jwt>`, sent to the **provider** | Logs, events, status, shell, attestation. Minted with `POST /v1/create-jwt-token`; see **@operations.md**. |

**API keys go in `x-api-key`, never in `Authorization: Bearer`.**

## API keys

### Format

```
ac.sk.production.<64 hex characters>
```

A key starting `ac.sk.` is a Console API key. AkashML keys start `akml-` and belong to a different service (`rules/deploy/akashml/`).

### Getting one

1. Sign up at [console.akash.network](https://console.akash.network). The account comes with its managed wallet.
2. Add credits under **Billing** (card via Stripe).
3. To deploy for a team, switch to that team first. A key acts in the personal account or team selected when it is created, and only there.
4. Open **Settings → API Keys** (`console.akash.network/user/api-keys`) and create a key. Leave it on **All projects**, or limit it to one project.
5. Copy it immediately. The full key is shown once; afterwards only a masked form (`ac.sk.production.abc123***def456`) is visible.

The first key always comes from the UI: every `/v1/api-keys` call needs an existing key or a Console session.

### Using one

Reference the key through an environment variable, never as a literal. The canonical name is `AKASH_API_KEY`.

```bash
curl https://console-api.akash.network/v1/deployments -H "x-api-key: $AKASH_API_KEY"
```

```typescript
const res = await fetch("https://console-api.akash.network/v1/deployments", {
  headers: { "x-api-key": process.env.AKASH_API_KEY! }
});
```

```python
import os, requests

res = requests.get(
    "https://console-api.akash.network/v1/deployments",
    headers={"x-api-key": os.environ["AKASH_API_KEY"]},
)
```

```go
req, _ := http.NewRequest("GET", "https://console-api.akash.network/v1/deployments", nil)
req.Header.Set("x-api-key", os.Getenv("AKASH_API_KEY"))
resp, err := http.DefaultClient.Do(req)
```

### Managing keys

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/v1/api-keys` | List your keys in the current team: `id`, `name`, `keyFormat` (masked), `organizationId`, `projectId`, `createdAt`, `lastUsedAt`, `expiresAt` |
| `POST` | `/v1/api-keys` | Create a key in the current team, optionally limited to one project with `projectId`. The response's `apiKey` is the only time the full key is returned. |
| `GET` | `/v1/api-keys/{id}` | One key's metadata |
| `PATCH` | `/v1/api-keys/{id}` | Rename: `{ "data": { "name": "..." } }`. Nothing else can change. |
| `DELETE` | `/v1/api-keys/{id}` | Revoke |

```bash
curl -sX POST https://console-api.akash.network/v1/api-keys \
  -H "x-api-key: $AKASH_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"data": {"name": "ci-prod-deploy", "expiresAt": "2027-01-01T00:00:00Z"}}'
```

```json
{
  "data": {
    "id": "6f1c...",
    "name": "ci-prod-deploy",
    "apiKey": "ac.sk.production.<copy this now>",
    "keyFormat": "ac.sk.production.9f2e4d***a17c03",
    "organizationId": "1b6e...",
    "projectId": null,
    "expiresAt": "2027-01-01T00:00:00.000Z",
    "createdAt": "...",
    "updatedAt": "...",
    "lastUsedAt": null
  }
}
```

`expiresAt` is optional; omit it for a key that doesn't expire.

### What a key can do

A key acts as the user who created it, in one place, never more than that user can:

- **One team.** `organizationId` is the personal account or team the key was created in, and every request runs there. It is `null` on keys from before teams, which act in their creator's personal account. A key can't switch teams: create one in each team it should deploy for.
- **The creator's role.** In a team, the key can do what its creator's role allows today: a `viewer` or `billing` member's key can't deploy, and once the creator leaves the team the key answers 403 `organization_forbidden`.
- **Optionally one project.** `projectId` limits the key to one project of its team; `null` means every project its creator reaches. A project key deploys into that project, can't touch other projects' deployments (403 `project_forbidden`), and can't manage keys, members or billing.

The binding is fixed: `PATCH` only renames. Give each service its own key, bound as narrowly as it needs, and revoke the ones you stop using. Details and the team errors: **@teams-and-projects.md**.

### Rotation

1. Create the new key (UI or `POST /v1/api-keys`).
2. Roll it out to every consumer.
3. Confirm traffic moved: the old key's `lastUsedAt` stops advancing.
4. Delete the old key.

## Public endpoints

These need no key:

| Endpoint | Returns |
|---|---|
| `GET /v1/providers`, `GET /v1/providers/{address}`, `GET /v1/provider-search` | Providers |
| `GET /v1/placement-options` | Regions and GPUs available now |
| `POST /v1/bid-screening` | Providers that would bid on a group |
| `GET /v1/deployment-funding-config` | Automatic funding constants |
| `GET /v1/deployment/{owner}/{dseq}` | Read-only view of any deployment |
| `GET /v1/balances?address=<akash1...>` | Balance split for any address. With a key and no `address`, the balance of the key's personal account or team. |
| `GET /v1/blockchain-status` | `{ "isBlockchainReachable": true }` |

## Auth errors

Errors use the shared envelope (see **@overview.md**).

| Status | Cause | Fix |
|---|---|---|
| 401 `Invalid API key` | The key is malformed, revoked, expired, or from another Console environment. The response doesn't say which. | Check the value starts `ac.sk.production.`, then list keys in the UI |
| 401 | The key went in `Authorization: Bearer`, or no credential was sent | Send it in `x-api-key` |
| 400 | Both `Authorization` and `x-api-key` were sent | Send only `x-api-key` |
| 403 | The key is valid but the account may not do this, such as a free-trial account over the trial's limits or without the Fair Use Policy accepted (`fair_use_policy_required`) | Act on the `code` and `message` |
| 403 `organization_forbidden` | The key's creator is no longer a member of the key's team | Use a key of a current member |
| 400 `organization_mismatch` | `x-organization-id` names another team than the key's | Drop the header; a key only acts in its own team |
| 403 `project_forbidden` | The request reaches a project the key can't, such as another project than the one it is bound to | Stay within the key's project (**@teams-and-projects.md**) |
| 403 `session_required` | The action needs a signed-in Console session: creating, leaving or deleting a team, accepting an invitation, deleting the account | Do it in the Console web app |

## CI/CD

Build JSON bodies with `jq` so a multi-line SDL is escaped correctly; never splice `$SDL` into a hand-written JSON string.

### GitHub Actions

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    env:
      AKASH_API_KEY: ${{ secrets.AKASH_API_KEY }}
    steps:
      - uses: actions/checkout@v4
      - name: Create the deployment
        run: |
          curl -sfX POST https://console-api.akash.network/v1/deployments \
            -H "x-api-key: $AKASH_API_KEY" \
            -H "Content-Type: application/json" \
            -d "$(jq -nc --rawfile sdl deploy.yaml '{data: {sdl: $sdl}}')"
```

### GitLab CI

```yaml
deploy:
  image: alpine:3.20
  before_script:
    - apk add --no-cache curl jq
  script:
    - >
      curl -sfX POST https://console-api.akash.network/v1/deployments
      -H "x-api-key: $AKASH_API_KEY"
      -H "Content-Type: application/json"
      -d "$(jq -nc --rawfile sdl deploy.yaml '{data: {sdl: $sdl}}')"
```

Store `AKASH_API_KEY` as a masked, protected CI/CD variable.

### Docker

Pass the key at run time: `docker run -e AKASH_API_KEY my-deployer`. Never bake it in with `ARG` or `ENV`; both survive in the image history.
