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
3. Open **Settings → API Keys** (`console.akash.network/user/api-keys`) and create a key.
4. Copy it immediately. The full key is shown once; afterwards only a masked form (`ac.sk.production.abc123***def456`) is visible.

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
| `GET` | `/v1/api-keys` | List keys: `id`, `name`, `keyFormat` (masked), `createdAt`, `lastUsedAt`, `expiresAt` |
| `POST` | `/v1/api-keys` | Create a key. The response's `apiKey` is the only time the full key is returned. |
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
    "expiresAt": "2027-01-01T00:00:00.000Z",
    "createdAt": "...",
    "updatedAt": "...",
    "lastUsedAt": null
  }
}
```

`expiresAt` is optional; omit it for a key that doesn't expire. Every key acts with the full rights of the account: there are no per-key scopes, so give each service its own key and revoke the ones you stop using.

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
| `GET /v1/balances?address=<akash1...>` | Balance split for any address. With your key and no `address`, your own. |
| `GET /v1/blockchain-status` | `{ "isBlockchainReachable": true }` |

## Auth errors

Errors use the shared envelope (see **@overview.md**).

| Status | Cause | Fix |
|---|---|---|
| 401 `Invalid API key` | The key is malformed, revoked, expired, or from another Console environment. The response doesn't say which. | Check the value starts `ac.sk.production.`, then list keys in the UI |
| 401 | The key went in `Authorization: Bearer`, or no credential was sent | Send it in `x-api-key` |
| 400 | Both `Authorization` and `x-api-key` were sent | Send only `x-api-key` |
| 403 | The key is valid but the account may not do this, such as a free-trial account over the trial's limits or without the Fair Use Policy accepted (`fair_use_policy_required`) | Act on the `code` and `message` |

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
