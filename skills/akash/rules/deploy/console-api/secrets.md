# Console API — Secrets

Console records each deployment's SDL so it can send manifests and take patches later. This file covers how values in that SDL are protected, and how to pass secrets that no endpoint ever returns.

## What Console stores readable

The stored SDL comes back from `GET /v1/deployments/{dseq}` (`consoleSettings.sdl`) and `GET /v2/deployment-settings/{dseq}` (`sdl`). Which values it shows depends on what the create said about secrets: `secretEnv`, `sealedSecrets`, or neither.

| Create request | Env values | Registry credentials |
|---|---|---|
| Neither `secretEnv` nor `sealedSecrets` | Every value is stored encrypted and shown as an `ac-secret://` reference | Encrypted |
| `secretEnv: ["NAME", ...]` | The named variables are stored encrypted. Every other value is stored as written. | Encrypted |
| `secretEnv: []` | Stored as written | Encrypted |
| `sealedSecrets` without `secretEnv`, even a seal of `{}` | Stored as written, except the ones the SDL references as `ac-secret://NAME` | Encrypted |

The container always receives the real values. So a plain SDL with secrets in `env` is already safe from later reads, at the cost of every env value becoming unreadable. For readable config plus a few real secrets, pick one of two ways:

- **Name them in `secretEnv`** (next section). No encryption on your side: the values travel in the SDL over TLS and Console encrypts the named ones before storing anything.
- **Reference them and seal them** (`ac-secret://` plus `sealedSecrets`, below). The values never appear in the SDL text or in the request body in plaintext.

## Naming the secret variables: `secretEnv`

`secretEnv` is a list of env variable names. Console encrypts the value of each named variable in every service that sets it, and stores every other env value as written, so it stays readable in the Console UI and in `consoleSettings.sdl`.

```bash
SDL=$(cat deploy.yaml)
curl -sX POST https://console-api.akash.network/v1/deployments \
  -H "x-api-key: $AKASH_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -nc --arg sdl "$SDL" '{data: {sdl: $sdl, secretEnv: ["SMTP_PASSWORD", "SESSION_SIGNING_KEY"]}}')"
```

With this SDL, `NODE_ENV` reads back as written and the other two read back as `ac-secret://` references:

```yaml
services:
  app:
    image: ghcr.io/acme/app:1.8.0
    env:
      - "NODE_ENV=production"
      - "SMTP_PASSWORD=<INSERT_SECRET>"
      - "SESSION_SIGNING_KEY=<INSERT_SECRET>"
```

- Names are env variable names, matched exactly and case-sensitively. They are not `ac-secret://` names.
- A name applies to every service in the SDL that sets that variable.
- `secretEnv: []` says no env value is secret: all of them stay readable.
- A name no service sets answers 400, so a typo can't leave a secret readable.
- Registry credentials are encrypted whatever the list says.
- The 201 response's `manifest` is built from the SDL you sent, so it repeats the values once. No later read returns them.
- `secretEnv` and `sealedSecrets` combine: `secretEnv` decides which plain values are encrypted, and `ac-secret://` references still take their values from the seal.

## Referencing a secret in the SDL

Replace the value with `ac-secret://NAME`:

```yaml
services:
  app:
    image: ghcr.io/acme/app:1.8.0
    env:
      - "NODE_ENV=production"
      - "SMTP_PASSWORD=ac-secret://SMTP_PASSWORD"
      - "SESSION_SIGNING_KEY=ac-secret://SESSION_SIGNING_KEY"
```

- `NAME` matches `[A-Za-z_][A-Za-z0-9_]{0,63}`, and the reference must be the whole value. `KEY=prefix-ac-secret://X` is not a reference.
- References work in `env` values and in a private registry's `credentials.username` and `credentials.password`.
- Any value starting with `ac-` is reserved: a value that starts with `ac-` but isn't a valid reference is refused.
- Every reference needs a value, and every sealed value needs a reference. Either mismatch answers 400.
- At most 100 secrets per deployment.

## Sealing the values

`sealedSecrets` is a compact JWE whose plaintext is a flat JSON object of names to string values, encrypted to Console's public key.

1. `GET /v1/sdl-secrets-context` returns `{ "data": { "kid", "sub", "jwk", "requiredClaims" } }`: the key to seal to, its key id, and your user id.
2. Encrypt the JSON with `alg: "RSA-OAEP-256"` and `enc: "A256GCM"`. Put these in the protected header:
   - `kid` and `sub`, copied from the context
   - `exp`: unix seconds, at most 15 minutes ahead (5 is a good default)
   - `sdlHash` (recommended on create): base64url of the SHA-256 of the **exact** `sdl` string you send. It binds the seal to that SDL, so the seal can't be replayed with another one.
3. Send it as `data.sealedSecrets` beside `data.sdl`.

Node.js with [`jose`](https://www.npmjs.com/package/jose):

```typescript
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { CompactEncrypt, importJWK } from "jose";

const API = "https://console-api.akash.network";
const headers = { "x-api-key": process.env.AKASH_API_KEY!, "Content-Type": "application/json" };

async function sealSecrets(secrets: Record<string, string>, sdl?: string): Promise<string> {
  const { data: context } = await (await fetch(`${API}/v1/sdl-secrets-context`, { headers })).json();
  const key = await importJWK({ ...context.jwk, alg: "RSA-OAEP-256" }, "RSA-OAEP-256");
  const sdlHash = sdl === undefined ? {} : { sdlHash: createHash("sha256").update(sdl, "utf8").digest("base64url") };

  return new CompactEncrypt(new TextEncoder().encode(JSON.stringify(secrets)))
    .setProtectedHeader({
      alg: "RSA-OAEP-256",
      enc: "A256GCM",
      kid: context.kid,
      sub: context.sub,
      exp: Math.floor(Date.now() / 1000) + 5 * 60,
      ...sdlHash
    })
    .encrypt(key);
}

const sdl = readFileSync("deploy.yaml", "utf8");
const sealedSecrets = await sealSecrets(
  {
    SMTP_PASSWORD: process.env.SMTP_PASSWORD!,
    SESSION_SIGNING_KEY: process.env.SESSION_SIGNING_KEY!
  },
  sdl
);

const res = await fetch(`${API}/v1/deployments`, {
  method: "POST",
  headers,
  body: JSON.stringify({ data: { sdl, sealedSecrets } })
});
const { data } = await res.json();
```

Hash the same string you put in `data.sdl`. Reformatting the YAML after hashing it gives a 403.

Python can do the same with `jwcrypto` or `authlib`; any JOSE library that supports `RSA-OAEP-256` with `A256GCM` and custom protected-header fields works.

## Changing secrets later

`PATCH /v1/deployments/{dseq}` takes a `sealedSecrets` holding only the names to replace; every other stored value stays. Seal it without `sdlHash`, because a patch is checked against the SDL Console stores rather than one you send. The new value reaches the workload through the deployment update the patch sends.

```json
{ "data": { "sealedSecrets": "<JWE of {\"SMTP_PASSWORD\": \"new-value\"}>" } }
```

A patch that writes env values through `services.<name>.env` stores all of them encrypted unless it says which are secret. `secretEnv` does that without a seal: it names the variables this patch writes whose values Console encrypts, and every other written value is stored as written.

```json
{
  "data": {
    "services": { "app": { "env": { "LOG_LEVEL": "debug", "SMTP_PASSWORD": "<INSERT_SECRET>" } } },
    "secretEnv": ["SMTP_PASSWORD"]
  }
}
```

- `secretEnv: []` keeps every value the patch writes readable.
- Variables the patch doesn't write keep what they hold, encrypted or readable. To encrypt a variable that is stored readable, write it again and name it.
- A name the patch doesn't write answers 400.
- A patch carrying `sealedSecrets` and no `secretEnv` also stores its written values as written; a seal of `{}` was the way to write a readable variable before `secretEnv`.

## Redeploying without re-entering values

`inheritSecretsFrom: "<dseq>"` on create starts the new deployment from the secrets stored for another deployment you can change in the same account or team, even a closed one. Values in `sealedSecrets` override inherited names. This is how to resize: take `consoleSettings.sdl` from the old deployment (its references are already in place), change the resources, create with `inheritSecretsFrom`, lease it, then close the old one.

## Errors

| Status | When | Fix |
|---|---|---|
| 400 | Malformed, tampered or expired seal; wrong `alg` or `enc`; a reference without a value; a sealed name nothing references; a `secretEnv` name the request sets no variable for | Fix the request |
| 403 | `sub` is not you, or `sdlHash` doesn't match the SDL | Reseal from a fresh context, hashing the exact SDL string |
| 409 | The seal names a key Console no longer holds | Fetch `GET /v1/sdl-secrets-context` again and reseal |
| 409 `inherited_secrets_unreadable` | The source deployment's secrets can no longer be decrypted | Permanent. Supply the values in `sealedSecrets`. |
| 503 | The key service is briefly unreachable | Retry |

## What secrets don't cover

- **Shell access.** A JWT with the `shell` scope can read the container's environment. Grant `shell` only where it's needed (**@operations.md**).
- **Self-custody deployments.** The CLI and SDKs send the manifest straight to the provider; nothing is sealed or stored.
