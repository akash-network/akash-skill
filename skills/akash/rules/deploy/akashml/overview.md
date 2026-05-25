# AkashML Overview

**AkashML** ([playground.akashml.com](https://playground.akashml.com)) is Akash Network's managed inference platform. It serves open-source AI models behind OpenAI- and Anthropic-compatible REST APIs, with the actual inference running on Akash decentralized GPU compute.

This is a **consumption** path, not a deployment path. You call an LLM endpoint with an API key; you do not write SDL, deposit ACT, or manage a deployment lifecycle. If you want to *host* a model yourself, see [@rules/sdl/examples/gpu-workload.md](../../sdl/examples/gpu-workload.md) and the four deployment methods documented elsewhere in this skill.

> **Always query the live API for catalog/pricing/capabilities.** Model IDs, prices, context lengths, and supported features change. Before recommending a model, quoting a price, or claiming a feature, call `GET /v1/models` (or `GET /anthropic/v1/models`) — the response includes pricing, `context_length`, `supported_features`, `supported_sampling_parameters`, `max_output_length`, and `quantization` per model. The examples in this file are illustrative; the API is authoritative.

## Base URLs

| Surface | Base URL | SDK compatibility |
|---|---|---|
| **OpenAI-compatible** | `https://api.akashml.com/v1` | `openai` (Python, Node), any OpenAI-compatible client — set `baseURL` and go |
| **Anthropic-compatible** | `https://api.akashml.com/anthropic` | `anthropic` (Python, Node), Claude Code via `ANTHROPIC_BASE_URL` |

Both surfaces serve the same underlying model catalog; pick the one that matches the SDK you're already using.

## When to use AkashML vs alternatives

| You want… | Use | Why |
|---|---|---|
| To **call** an LLM (chat, completion, RAG) without owning the box | **AkashML** | Managed, OpenAI/Anthropic-compatible, credit-billed, no SDL |
| To **host** your own model (custom weights, fine-tunes, persistent state) | **SDL + GPU profile** ([gpu-workload.md](../../sdl/examples/gpu-workload.md)) | You control the runtime, weights, persistence; you pay in ACT |
| A web chat UI for an open model (one-off, no integration) | [playground.akashml.com](https://playground.akashml.com) | Browser-only; no code needed |
| Inference *plus* fine-tuning or model upload | Self-deploy via SDL | AkashML does not expose fine-tuning APIs |

If a user says *"I want to run Llama on Akash"* — that's ambiguous. Ask **one** short question: *"Do you want to call a hosted model, or run your own instance?"* — and then commit. The two answers go to completely different files.

## Auth at a glance

- **OpenAI surface:** `Authorization: Bearer $AKASHML_API_KEY`
- **Anthropic surface:** `Authorization: Bearer $AKASHML_API_KEY`

Both surfaces use the same Bearer scheme. The API key format starts with `akml-`. See [@authentication.md](authentication.md) for the full key-management flow.

## Models

The catalog is dynamic — always query `GET /v1/models` (or `GET /anthropic/v1/models`) for the current list rather than hardcoding model IDs in prose. Observed at the time of writing: open-source models from MiniMax, DeepSeek, Moonshot (Kimi), Meta (Llama), and Qwen families.

`GET /v1/models` returns per-model **pricing**, **context length**, **supported features** (chat, tools, streaming, reasoning), and **supported sampling parameters** — read these from the API rather than hardcoding assumptions about a model's capabilities. The Anthropic surface's `GET /anthropic/v1/models` returns IDs with slashes aliased to `--` (because Claude Code-shaped clients reject slashes); both surfaces accept either form on calls.

See [@api-reference.md](api-reference.md) for the listing call and example response shape.

## Billing — important: not the same as Console API

AkashML billing is **USD credits** on the AkashML account, not on-chain ACT. Do not confuse with Console API (which also accepts USD but converts to `uact` server-side for the on-chain deployment escrow):

| Platform | Billing | Underlying token |
|---|---|---|
| **AkashML** | USD credits via Stripe | Off-chain; AkashML pays providers on your behalf |
| **Console API** | USD via Stripe → managed wallet | On-chain `uact` for deployment escrow |
| **CLI / SDK** | You hold AKT, burn to ACT | On-chain `uact` for deployment escrow |

See [@account-and-billing.md](account-and-billing.md) for the credit model details.

## Stability

AkashML is a production-managed service. Treat it as you would any third-party inference provider:

- **Pin model IDs** in committed code (not "latest"). The catalog can change.
- **Distinguish `402` from `429`.** `402 Payment Required` means you're out of credits — retrying won't help, you have to top up. `429 Too Many Requests` is a transient per-key rate limit; back off and retry.
- **Honor `Retry-After` and `X-RateLimit-*` headers** on `429`.
- **Capture `Inference-Id`** from response headers for support requests.
- **Expect occasional model deprecations** — verify your pinned model is still listed before a release.

## Related files

- **[@authentication.md](authentication.md)** — API key creation, header conventions, env-var rules
- **[@api-reference.md](api-reference.md)** — OpenAI + Anthropic endpoints with curl/SDK examples
- **[@quickstart.md](quickstart.md)** — Linear walkthrough from signup to first inference call
- **[@account-and-billing.md](account-and-billing.md)** — Credits, top-up, rate limits
- **[@claude-code-integration.md](claude-code-integration.md)** — Point Claude Code at AkashML
