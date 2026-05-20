# Console API Authentication

The Console API supports two authentication schemes. Pick the right header for the credential you have.

| Credential | Header | Use case |
|---|---|---|
| **API key** | `x-api-key: <key>` | Long-lived programmatic access (CI/CD, backends, scripts) |
| **JWT (Console session)** | `Authorization: Bearer <jwt>` | Short-lived browser/session auth |

**Critical:** API keys go in `x-api-key`. They do **not** go in `Authorization: Bearer`. That header is for JWT tokens only.

A few read-only endpoints are public (no auth) — provider lists, network capacity, blockchain explorer queries — but every deployment-management endpoint requires one of the two schemes above.

## API key authentication

### Getting an API key

1. Visit https://console.akash.network and sign up (email + password). Your account is automatically provisioned with a managed wallet.
2. Fund the wallet via Stripe under Settings → Payment Methods.
3. Generate an API key under Settings → API Keys.
4. Copy the key **immediately** — the plaintext value is shown exactly once. After that the key is hashed and you can only see the metadata.

### Using an API key

```bash
curl https://console-api.akash.network/v1/deployments \
  -H "x-api-key: $AKASH_API_KEY"
```

### Best practices

- **Never** commit keys to version control.
- Store in environment variables or a secrets manager (Vault, AWS Secrets Manager, GitHub Actions secrets, etc.).
- Use separate keys for dev/staging/prod.
- Rotate keys periodically — generate the new one, deploy it, then delete the old one.
- Give each key a descriptive name so you know which service uses it.

### Code examples

**Node.js (fetch):**
```typescript
const API_KEY = process.env.AKASH_API_KEY!;

const response = await fetch("https://console-api.akash.network/v1/deployments", {
  headers: { "x-api-key": API_KEY }
});
```

**Python (requests):**
```python
import os, requests

api_key = os.environ["AKASH_API_KEY"]
response = requests.get(
    "https://console-api.akash.network/v1/deployments",
    headers={"x-api-key": api_key}
)
```

**Go:**
```go
apiKey := os.Getenv("AKASH_API_KEY")

req, _ := http.NewRequest("GET", "https://console-api.akash.network/v1/deployments", nil)
req.Header.Set("x-api-key", apiKey)

resp, _ := http.DefaultClient.Do(req)
```

## API Keys CRUD

The Console API exposes endpoints to manage API keys programmatically (you can also do this through the Console UI).

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/v1/api-keys` | List your API keys (metadata only — no plaintext) |
| `POST` | `/v1/api-keys` | Create a new key. **The plaintext value is returned exactly once.** |
| `GET` | `/v1/api-keys/{id}` | Read metadata for one key |
| `PATCH` | `/v1/api-keys/{id}` | Rename a key (the only mutation allowed) |
| `DELETE` | `/v1/api-keys/{id}` | Revoke a key |

### Create

```bash
curl -X POST https://console-api.akash.network/v1/api-keys \
  -H "x-api-key: $AKASH_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "name": "ci-prod-deploy",
      "expiresAt": "2027-01-01T00:00:00Z"
    }
  }'
```

Response (201 Created):

```json
{
  "data": {
    "id": "...",
    "name": "ci-prod-deploy",
    "apiKey": "<the plaintext key — copy now>",
    "createdAt": "...",
    "expiresAt": "2027-01-01T00:00:00Z"
  }
}
```

`expiresAt` is optional. Omit it for a non-expiring key.

### Revoke

```bash
curl -X DELETE https://console-api.akash.network/v1/api-keys/<id> \
  -H "x-api-key: $AKASH_API_KEY"
```

## JWT authentication

JWTs are used in two contexts:

1. **Console session auth** — the Console web app authenticates the user and uses a JWT to call the API on their behalf. You generally don't need this from a script.
2. **Provider access tokens** — short-lived JWTs that let a client call the provider directly (logs, events, status, shell). This is the important one for programmatic use.

### Provider access JWT (the one you'll use)

To stream logs from a deployment's provider, you need a JWT that the provider will accept.

#### For Console-account users (this skill's primary path)

Mint via the Console API:

```bash
curl -X POST https://console-api.akash.network/v1/create-jwt-token \
  -H "x-api-key: $AKASH_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "ttl": 1800,
      "leases": {
        "access": "scoped",
        "scope": ["status", "logs", "events", "shell"]
      }
    }
  }'
```

Response:

```json
{ "data": { "token": "<jwt>" } }
```

`ttl` is in seconds (Console uses 1800 = 30 minutes by default). The `leases` object follows AEP-64:

| Form | Shape | Use |
|---|---|---|
| Full | `{ "access": "full", "scope": ["logs", ...] }` | All scopes across all of your leases |
| Scoped | `{ "access": "scoped", "scope": [...] }` | All leases, restricted scopes |
| Granular | `{ "access": "granular", "permissions": [{ "provider": "...", "access": "scoped", "scope": [...], "deployments": [{ "dseq": "...", "gseq": 1, "scope": [...] }] }] }` | Per-provider, per-deployment scopes |

Valid scope values: `send-manifest`, `get-manifest`, `logs`, `shell`, `events`, `status`, `restart`.

#### For self-custody users (CLI / SDK)

`/v1/create-jwt-token` is **not** for you. The Console can't sign with a key it doesn't hold. Sign the JWT locally using `@akashnetwork/chain-sdk`:

```typescript
import { JwtTokenManager } from "@akashnetwork/chain-sdk";

const mgr = new JwtTokenManager(wallet); // wallet exposes signing key
const token = await mgr.generateToken({
  iss: address,
  iat: Math.floor(Date.now() / 1000),
  exp: Math.floor(Date.now() / 1000) + 1800,
  version: "v1",
  leases: { access: "scoped", scope: ["status", "logs", "events"] }
});
```

The JWT payload schema is defined by AEP-64. Once minted, the JWT goes in `Authorization: Bearer <jwt>` on the call to the provider — exactly the same as the managed-wallet flow.

### Using the JWT

The JWT is sent to the **provider** (not the Console API) when fetching logs/events/status. The Console API never proxies these requests. See **@operations.md** for provider URL templates.

```bash
JWT=$(curl -sX POST https://console-api.akash.network/v1/create-jwt-token \
  -H "x-api-key: $AKASH_API_KEY" \
  -d '{"data":{"ttl":1800,"leases":{"access":"scoped","scope":["logs"]}}}' \
  | jq -r .data.token)

# Then call the provider directly
curl "https://<provider-host>/lease/<dseq>/<gseq>/<oseq>/status" \
  -H "Authorization: Bearer $JWT"
```

### JWT refresh

There is **no** `/v1/auth/refresh` endpoint. To refresh, call `POST /v1/create-jwt-token` again with a fresh `ttl`. JWTs are short-lived by design; rotate them, don't try to extend them.

## Public endpoints

A handful of endpoints don't require authentication:

| Endpoint | Description |
|---|---|
| `GET /v1/providers` | List providers |
| `GET /v1/providers/{address}` | Provider details |
| `GET /v1/balances?address=` | Read on-chain balance for any address |
| `GET /v1/blockchain-status` | Reachability check |
| `POST /v1/bid-screening` | Match deployment requirements to providers (no chain action) |
| `POST /v1/pricing` | Price estimate for given compute resources |

These are safe to call from scripts without credentials.

## Error responses

### 401 Unauthorized

Missing, malformed, or expired credential. Check:

- API key in `x-api-key` (not `Authorization`)
- JWT not expired (`exp` claim)
- Key not deleted

### 403 Forbidden

Credential valid but not permitted for this action. For API keys this usually means the key was created with restrictions; for JWTs it means the `leases` scope on the token doesn't grant the requested operation.

### 429 Rate Limited

```json
{ "error": { "code": "RATE_LIMITED", "message": "Too many requests", "retryAfter": 60 } }
```

Honor `Retry-After`; back off exponentially.

### Retry wrapper

```typescript
async function fetchWithRetry(url: string, options: RequestInit, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    const response = await fetch(url, options);
    if (response.status !== 429) return response;
    const retryAfter = parseInt(response.headers.get("Retry-After") ?? "60", 10);
    await new Promise((r) => setTimeout(r, retryAfter * 1000));
  }
  throw new Error("Max retries exceeded");
}
```

## Security notes

### Storage

- **Do:** environment variables, secrets manager, encrypted at rest.
- **Don't:** hardcoded in source, committed to git, logged.

### Key rotation

1. Create a new key via `POST /v1/api-keys`.
2. Roll out to all consumers.
3. Verify the new key works.
4. Delete the old key via `DELETE /v1/api-keys/<id>`.

### Monitoring

Watch for unusual patterns: spikes in 401s (rotated key not propagated), 403s (scope mismatch), 429s (need a higher tier or better backoff).

## CI/CD integration

### GitHub Actions

```yaml
env:
  AKASH_API_KEY: ${{ secrets.AKASH_API_KEY }}

steps:
  - name: Deploy to Akash
    run: |
      curl -X POST https://console-api.akash.network/v1/deployments \
        -H "x-api-key: $AKASH_API_KEY" \
        -H "Content-Type: application/json" \
        -d "{\"data\":{\"sdl\":\"$SDL\",\"deposit\":5}}"
```

### GitLab CI

```yaml
deploy:
  variables:
    AKASH_API_KEY: $AKASH_API_KEY  # configured in CI/CD settings
  script:
    - |
      curl -X POST https://console-api.akash.network/v1/deployments \
        -H "x-api-key: $AKASH_API_KEY" \
        -H "Content-Type: application/json" \
        -d "{\"data\":{\"sdl\":\"$SDL\",\"deposit\":5}}"
```

### Docker

Pass the key at runtime, not at build time:

```bash
docker run -e AKASH_API_KEY=$AKASH_API_KEY my-deploy-image
```

Do not bake the key into image layers via `ARG` — it survives in the image history.
