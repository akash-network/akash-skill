# AkashML Authentication

AkashML uses **API keys** for all programmatic access. Both the OpenAI- and Anthropic-compatible surfaces accept the same key in an `Authorization: Bearer` header.

| Surface | Header | Example |
|---|---|---|
| OpenAI (`/v1/*`) | `Authorization: Bearer <key>` | `Authorization: Bearer akml-...` |
| Anthropic (`/anthropic/*`) | `Authorization: Bearer <key>` | `Authorization: Bearer akml-...` |

There is no `x-api-key` header on AkashML. (This differs from the Akash **Console API**, which uses `x-api-key` — see [@../console-api/authentication.md](../console-api/authentication.md). Different platform, different key, different header.)

## Getting an API key

1. Sign up at [playground.akashml.com](https://playground.akashml.com).
2. Verify your email.
3. Add a payment method (Settings → Billing). Trial credits unlock after verification.
4. Generate an API key under **Settings → API Keys**. Copy it immediately — the plaintext value is shown exactly once.

Keys begin with the prefix `akml-`. The prefix is a quick sanity check that you have the right kind of key in hand (it is *not* a Console API key).

## Using the key

Always reference the key via an environment variable. The canonical name in this skill is `AKASHML_API_KEY` — distinct from `AKASH_API_KEY` (which belongs to the Console API).

**curl (OpenAI surface):**

```bash
curl https://api.akashml.com/v1/models \
  -H "Authorization: Bearer $AKASHML_API_KEY"
```

**curl (Anthropic surface):**

```bash
curl https://api.akashml.com/anthropic/v1/models \
  -H "Authorization: Bearer $AKASHML_API_KEY"
```

**Python (`openai` SDK):**

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["AKASHML_API_KEY"],
    base_url="https://api.akashml.com/v1",
)
```

**Python (`anthropic` SDK):**

```python
import os
from anthropic import Anthropic

client = Anthropic(
    api_key=os.environ["AKASHML_API_KEY"],
    base_url="https://api.akashml.com/anthropic",
)
```

**Node (`openai` SDK):**

```typescript
import OpenAI from "openai";

const client = new OpenAI({
  apiKey: process.env.AKASHML_API_KEY,
  baseURL: "https://api.akashml.com/v1",
});
```

**Node (`@anthropic-ai/sdk`):**

```typescript
import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic({
  apiKey: process.env.AKASHML_API_KEY,
  baseURL: "https://api.akashml.com/anthropic",
});
```

The only thing that changes from a stock OpenAI/Anthropic setup is `baseURL`. Everything else — request shape, response shape, streaming, tool use — follows the upstream SDK contract.

## Key handling rules (apply silently)

These are the same rules as Console API in [@../../../SKILL.md](../../../SKILL.md) "API key handling" — applied identically to AkashML keys:

1. **Always reference the key via env var** in code: `$AKASHML_API_KEY` / `process.env.AKASHML_API_KEY` / `os.environ["AKASHML_API_KEY"]` / `os.Getenv("AKASHML_API_KEY")`.
2. **Never echo a literal key** in code or chat, even if the user pasted one. Replace with `$AKASHML_API_KEY` and add one sentence: *"I've used `$AKASHML_API_KEY` in the code below — export your key as that env var before running."*

### When to add extra guidance (one of these, pick the smallest)

- User pastes a literal key → one-sentence redirect to env var. Don't lecture.
- User asks where to put the key for a specific runtime (GitHub Actions, Docker, etc.) → answer for that runtime in one line.
- User writing a Dockerfile → pass at runtime (`-e`), not baked in via `ARG`/`ENV`. One sentence.
- User mentions `.env` → one-line `.gitignore` reminder.

### Stay silent when

- User already said the key is in `$AKASHML_API_KEY` / `${{ secrets.AKASHML_API_KEY }}` — they've got it.
- The conversation has moved past auth (model selection, prompt engineering, response handling).

## Per-key limits

Each key carries configurable limits, set in the AkashML dashboard, **not** via API:

| Limit | Meaning |
|---|---|
| **RPM** | Requests per minute |
| **TPM** | Tokens per minute (input + output) |
| **Concurrent** | Simultaneous in-flight requests |
| **Expiration** | Optional ISO 8601 date when the key stops working |

Exceeding any rate limit returns `429 Too Many Requests`. Inspect the response headers:

| Header | Meaning |
|---|---|
| `Retry-After` | Seconds to wait before retrying |
| `X-RateLimit-Limit` | Total requests allowed in the window |
| `X-RateLimit-Remaining` | Requests remaining |
| `X-RateLimit-Reset` | Unix timestamp when the limit resets |

```typescript
async function callWithRetry(fn: () => Promise<Response>, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    const response = await fn();
    if (response.status !== 429) return response;
    const retryAfter = parseInt(response.headers.get("Retry-After") ?? "5", 10);
    await new Promise((r) => setTimeout(r, retryAfter * 1000));
  }
  throw new Error("Max retries exceeded");
}
```

## Storage and rotation

- **Do:** env vars, secrets manager, encrypted at rest.
- **Don't:** hardcode in source, commit to git, log.
- **Rotate** by creating a new key in the dashboard, deploying it, then deleting the old one.
- Use **separate keys per environment** (dev / staging / prod) so you can revoke without taking down everything.

## CI/CD examples

**GitHub Actions:**

```yaml
env:
  AKASHML_API_KEY: ${{ secrets.AKASHML_API_KEY }}

steps:
  - name: Run inference smoke test
    run: |
      curl -fsS https://api.akashml.com/v1/models \
        -H "Authorization: Bearer $AKASHML_API_KEY" > /dev/null
```

**GitLab CI:**

```yaml
smoke-test:
  variables:
    AKASHML_API_KEY: $AKASHML_API_KEY  # configured in CI/CD settings (mask + protect)
  script:
    - |
      curl -fsS https://api.akashml.com/v1/models \
        -H "Authorization: Bearer $AKASHML_API_KEY" > /dev/null
```

**Docker (runtime, not build):**

```bash
docker run -e AKASHML_API_KEY=$AKASHML_API_KEY my-inference-image
```

Never bake the key in via `ARG` / `ENV` — it survives in image layer history.

## Common pitfalls

| Symptom | Likely cause | Fix |
|---|---|---|
| `401 Unauthorized` | Missing or malformed key | Confirm `Authorization: Bearer <key>` (not `x-api-key`) |
| `401 Unauthorized` | Used a Console API key (`AKASH_API_KEY`) instead of an AkashML key (`AKASHML_API_KEY`) | They are different services; use the `akml-...` key |
| `402 Payment Required` | **Insufficient credits** on the AkashML account | Top up in the dashboard, or enable auto-top-up |
| `403 Forbidden` | Key revoked or model not permitted for this key | Check the AkashML dashboard |
| `429 Too Many Requests` | Hit RPM/TPM/concurrent limit | Honor `Retry-After`; consider higher limit in dashboard |
| Streaming hangs | Client timeout too low for long generations | Raise client timeout (Claude Code uses `API_TIMEOUT_MS=3000000` — 50 minutes) |

> **Capture `Inference-Id`.** Every successful inference response includes an `Inference-Id` header. Log it on the client side; AkashML support will ask for it when debugging a specific call.

## Related files

- **[@overview.md](overview.md)** — Base URLs, when to use, model catalog notes
- **[@api-reference.md](api-reference.md)** — Full endpoint reference
- **[@quickstart.md](quickstart.md)** — End-to-end first call
- **[@account-and-billing.md](account-and-billing.md)** — Credits, top-up, rate-limit semantics
- **[@claude-code-integration.md](claude-code-integration.md)** — Special env-var setup for Claude Code
