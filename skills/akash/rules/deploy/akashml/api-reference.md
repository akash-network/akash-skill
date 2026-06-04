# AkashML API Reference

> **Hit the live endpoints — don't trust this file's snapshots.** Model IDs, prices, context lengths, and supported features change. Before recommending a model or quoting numbers, call `GET /v1/models` (or `GET /anthropic/v1/models`) and read the live response. The shapes documented here are stable; the *contents* of model lists, pricing, and feature flags are not.

AkashML exposes two HTTP surfaces that follow established schemas. Both accept the same `Authorization: Bearer $AKASHML_API_KEY` header.

| Surface | Base URL | Schema | Use when |
|---|---|---|---|
| **OpenAI-compatible** | `https://api.akashml.com/v1` | OpenAI REST API | You already use the `openai` SDK or generic OpenAI tooling |
| **Anthropic-compatible** | `https://api.akashml.com/anthropic` | Anthropic Messages API | You already use the `anthropic` SDK, Claude Code, or Anthropic-shaped clients |

Pick the surface that matches your existing client. Both are served by the same backend; the request/response shapes are the only difference.

## OpenAI-compatible endpoints

### `GET /v1/models` — list models

```bash
curl https://api.akashml.com/v1/models \
  -H "Authorization: Bearer $AKASHML_API_KEY"
```

Returns the standard OpenAI list shape, enriched with AkashML-specific metadata (pricing, context length, capabilities):

```json
{
  "object": "list",
  "data": [
    {
      "id": "MiniMaxAI/MiniMax-M2.5",
      "object": "model",
      "created": 1700000000,
      "owned_by": "akashml",
      "name": "MiniMax M2.5",
      "context_length": 200000,
      "input_modalities": ["text"],
      "output_modalities": ["text"],
      "supported_features": ["chat", "tools", "streaming"],
      "supported_sampling_parameters": ["temperature", "top_p", "top_k", "frequency_penalty"],
      "max_output_length": 8192,
      "quantization": "fp8",
      "pricing": {
        "input":  "0.20",
        "output": "1.00",
        "request": "0"
      }
    }
  ]
}
```

Per-model `pricing` is per **million tokens** (USD). Read it from this endpoint rather than hardcoding — pricing changes.

Requires auth — calling without a key returns `401 Unauthorized`.

### `POST /v1/chat/completions` — chat completion

Standard OpenAI Chat Completions contract. Required fields: `model`, `messages`. Common optional fields: `max_completion_tokens` (preferred over the legacy `max_tokens`), `temperature`, `top_p`, `stop`, `tools`, `tool_choice`, `response_format`, `stream`, `seed`.

The response includes an **`Inference-Id`** header — capture it; you'll need it when contacting support about a specific call.

**curl:**

```bash
curl -X POST https://api.akashml.com/v1/chat/completions \
  -H "Authorization: Bearer $AKASHML_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "MiniMaxAI/MiniMax-M2.5",
    "messages": [
      {"role": "system", "content": "You are a concise assistant."},
      {"role": "user", "content": "Summarize the Akash Network in one sentence."}
    ],
    "max_completion_tokens": 200
  }'
```

**Python (`openai` SDK):**

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["AKASHML_API_KEY"],
    base_url="https://api.akashml.com/v1",
)

response = client.chat.completions.create(
    model="MiniMaxAI/MiniMax-M2.5",
    messages=[
        {"role": "system", "content": "You are a concise assistant."},
        {"role": "user", "content": "Summarize the Akash Network in one sentence."},
    ],
    max_completion_tokens=200,
)

print(response.choices[0].message.content)
```

**Node (`openai` SDK):**

```typescript
import OpenAI from "openai";

const client = new OpenAI({
  apiKey: process.env.AKASHML_API_KEY,
  baseURL: "https://api.akashml.com/v1",
});

const response = await client.chat.completions.create({
  model: "MiniMaxAI/MiniMax-M2.5",
  messages: [
    { role: "system", content: "You are a concise assistant." },
    { role: "user", content: "Summarize the Akash Network in one sentence." },
  ],
  max_completion_tokens: 200,
});

console.log(response.choices[0].message.content);
```

#### Akash-specific extension: `reasoning`

The OpenAI surface accepts an Akash-specific `reasoning` object that controls thinking-style models:

```json
{
  "model": "...",
  "messages": [...],
  "reasoning": {
    "effort": "high",
    "max_tokens": 4096,
    "exclude": false,
    "enabled": true
  }
}
```

| Field | Meaning |
|---|---|
| `effort` | `xhigh` / `high` / `medium` / `low` / `minimal` / `none` (accepted values vary by model) |
| `max_tokens` | Max tokens spent on reasoning |
| `exclude` | If true, reasoning tokens are stripped from the response |
| `enabled` | Whether to enable reasoning at all |

This is non-portable to vanilla OpenAI — guard the field behind a feature flag if your code targets both AkashML and `api.openai.com`.

### Streaming chat completion

Add `stream: true` and consume the SSE stream the SDK exposes. The stream emits `data:` lines and terminates with `data: [DONE]`. Pass `stream_options: { include_usage: true }` if you need a final usage chunk.

```typescript
const stream = await client.chat.completions.create({
  model: "MiniMaxAI/MiniMax-M2.5",
  messages: [{ role: "user", content: "Stream a haiku about decentralized compute." }],
  stream: true,
  stream_options: { include_usage: true },
});

for await (const chunk of stream) {
  process.stdout.write(chunk.choices[0]?.delta?.content ?? "");
}
```

curl with raw SSE:

```bash
curl -N -X POST https://api.akashml.com/v1/chat/completions \
  -H "Authorization: Bearer $AKASHML_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"MiniMaxAI/MiniMax-M2.5","messages":[{"role":"user","content":"hi"}],"stream":true}'
```

### `POST /v1/completions` — legacy completion

Same auth and shape as the upstream OpenAI legacy completion endpoint. Prefer `/v1/chat/completions` for new code; this exists for compatibility with older clients.

## Anthropic-compatible endpoints

### `GET /anthropic/v1/models` — list models

```bash
curl https://api.akashml.com/anthropic/v1/models \
  -H "Authorization: Bearer $AKASHML_API_KEY"
```

Response shape mirrors Anthropic's list-models response:

```json
{
  "data": [
    {
      "type": "model",
      "id": "MiniMaxAI--MiniMax-M2.5",
      "display_name": "MiniMax M2.5",
      "created_at": "2026-01-15T00:00:00Z"
    }
  ],
  "has_more": false,
  "first_id": "MiniMaxAI--MiniMax-M2.5",
  "last_id": "MiniMaxAI--MiniMax-M2.5"
}
```

This endpoint is reachable **without** auth (returns `200` even with no key), so it doubles as an unauthenticated reachability probe. (`GET /v1/models` on the OpenAI surface, by contrast, requires a Bearer key.)

**Model ID aliasing on the Anthropic surface.** Slashes in upstream IDs are aliased with `--` (e.g., `anthropic/claude-3-5-sonnet` → `anthropic--claude-3-5-sonnet`) — this exists because Claude Code rejects model IDs containing `/`. The list-models endpoint returns the aliased form. The Messages endpoint accepts either form (the canonical slashed form *and* the aliased form), so use whichever your client tolerates. If in doubt, pass the aliased form to play safe with Claude-Code-shaped clients.

### `POST /anthropic/v1/messages` — create message

Required fields: `model`, `messages`, `max_tokens` (Anthropic mandates `max_tokens` — not optional like on OpenAI). Common optional fields: `system`, `temperature`, `top_p`, `top_k`, `stop_sequences`, `stream`, `tools`, `tool_choice`, `thinking`, `metadata`.

**curl:**

```bash
curl -X POST https://api.akashml.com/anthropic/v1/messages \
  -H "Authorization: Bearer $AKASHML_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "MiniMaxAI/MiniMax-M2.5",
    "max_tokens": 256,
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'
```

**Python (`anthropic` SDK):**

```python
import os
from anthropic import Anthropic

client = Anthropic(
    api_key=os.environ["AKASHML_API_KEY"],
    base_url="https://api.akashml.com/anthropic",
)

response = client.messages.create(
    model="MiniMaxAI/MiniMax-M2.5",
    max_tokens=256,
    messages=[{"role": "user", "content": "Hello!"}],
)

print(response.content[0].text)
```

**Node (`@anthropic-ai/sdk`):**

```typescript
import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic({
  apiKey: process.env.AKASHML_API_KEY,
  baseURL: "https://api.akashml.com/anthropic",
});

const response = await client.messages.create({
  model: "MiniMaxAI/MiniMax-M2.5",
  max_tokens: 256,
  messages: [{ role: "user", content: "Hello!" }],
});

console.log(response.content[0].type === "text" ? response.content[0].text : "");
```

#### Extended thinking

Pass a `thinking` object to enable Anthropic-shaped reasoning traces:

```json
{
  "model": "...",
  "messages": [...],
  "max_tokens": 4096,
  "thinking": { "type": "enabled", "budget_tokens": 2048 }
}
```

The response's `content` array will include `thinking` blocks alongside `text` and `tool_use` blocks. Support depends on the chosen model — check the `supported_features` field from the OpenAI-surface `/v1/models` listing.

### Streaming messages

```python
with client.messages.stream(
    model="MiniMaxAI/MiniMax-M2.5",
    max_tokens=256,
    messages=[{"role": "user", "content": "Stream a haiku."}],
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
```

When `stream: true` is set, the response content type switches to `text/event-stream` and Anthropic-shaped events are emitted:

| Event | Meaning |
|---|---|
| `message_start` | Message envelope (id, model, role, usage) |
| `content_block_start` | A new content block begins (text, tool_use, thinking) |
| `content_block_delta` | Incremental content (text delta, input_json_delta, thinking_delta) |
| `content_block_stop` | End of a content block |
| `message_delta` | Running `stop_reason` / `usage` updates |
| `message_stop` | Terminal event |
| `ping` | Keep-alive |
| `error` | Terminal error event (see error type mapping below) |

The `anthropic` SDK abstracts these events; raw SSE consumers need to parse the event names.

## Model IDs across surfaces

Canonical AkashML model IDs use slashes (e.g., `MiniMaxAI/MiniMax-M2.5`). Both surfaces accept the slashed form. The Anthropic-surface list-models endpoint also returns each ID in a `--` aliased form because Claude Code (and clients of the same shape) reject slashed identifiers:

| Canonical (works on both surfaces) | Anthropic-surface aliased form (returned by `GET /anthropic/v1/models`) |
|---|---|
| `MiniMaxAI/MiniMax-M2.5` | `MiniMaxAI--MiniMax-M2.5` |
| `deepseek-ai/DeepSeek-V4-Flash` | `deepseek-ai--DeepSeek-V4-Flash` |
| `moonshotai/Kimi-K2.6` | `moonshotai--Kimi-K2.6` |
| `Qwen/Qwen3.5-35B-A3B` | `Qwen--Qwen3.5-35B-A3B` |

Rule of thumb: use the slashed form unless your client rejects slashes (Claude Code-shaped clients do). If you list and capture IDs at runtime, use whatever form the listing returned — don't translate by hand.

## Tool use, JSON mode, vision

These features follow the upstream SDK contract for each surface:

- **OpenAI surface** — `tools`, `tool_choice`, `response_format: { type: "json_object" }`, vision content blocks all behave as the OpenAI docs describe, *to the extent the underlying model supports them*. Not every open-source model supports tool calls; check the model card.
- **Anthropic surface** — `tools`, `tool_choice`, vision content blocks via `image` source — same caveat: support depends on the model.

If a feature isn't supported by the model, the call either errors or silently degrades. Test against your chosen model rather than assuming parity with first-party OpenAI/Anthropic models.

## Error responses

The two surfaces use different error envelopes — OpenAI's `{ "error": { ... } }` and Anthropic's `{ "type": "error", "error": { type, message } }` — and slightly different status-code surfaces.

### OpenAI surface (`/v1/*`)

| Status | Meaning | Action |
|---|---|---|
| `400` | Malformed request | Fix the request body |
| `401` | Bad / missing key | Check `Authorization: Bearer ...` and that the key is `akml-...` |
| `402` | **Insufficient credits** | Top up the AkashML account (or enable auto-top-up) |
| `429` | Rate limited (RPM / TPM / concurrent) | Honor `Retry-After` + `X-RateLimit-Reset`; back off |
| `500` | Internal server error | Retry with backoff |
| `504` | No backend available | Retry with backoff; consider a fallback model |
| `529` | No healthy backends for this model | Retry with backoff; consider a fallback model |

### Anthropic surface (`/anthropic/*`)

Anthropic responses carry a typed error category in `error.type`. Status → `error.type`:

| Status | `error.type` |
|---|---|
| `400` | `invalid_request_error` |
| `401` | `authentication_error` |
| `403` | `permission_error` |
| `404` | `not_found_error` |
| `413` | `request_too_large` |
| `429` | `rate_limit_error` (response includes `Retry-After`) |
| `500` | `api_error` |
| `503` / `529` | `overloaded_error` |

### Rate-limit response headers

Both surfaces return these when limiting kicks in:

| Header | Meaning |
|---|---|
| `Retry-After` | Seconds to wait before retrying |
| `X-RateLimit-Limit` | Total requests allowed in the current window |
| `X-RateLimit-Remaining` | Requests remaining in the current window |
| `X-RateLimit-Reset` | Unix timestamp when the limit resets |

Prefer `Retry-After` for backoff timing; fall back to `X-RateLimit-Reset` if `Retry-After` is missing.

## Health probes

Both surfaces expose informal health endpoints (best-effort, not contractual):

- `GET https://api.akashml.com/anthropic/v1/models` — unauthenticated reachability check (returns `200` with no key)
- `GET https://api.akashml.com/anthropic` — base reachability check

For a real smoke test that also validates auth, do `GET /v1/models` with your key — that endpoint requires a Bearer key (`401` without), so it checks both reachability and authentication.

## Related files

- **[@overview.md](overview.md)** — Surface selection, when to use AkashML
- **[@authentication.md](authentication.md)** — Key creation, env-var conventions, CI/CD
- **[@quickstart.md](quickstart.md)** — Step-by-step first call
- **[@claude-code-integration.md](claude-code-integration.md)** — Anthropic-surface env-var setup for Claude Code
