# AkashML Quickstart — From Signup to First Inference Call

A linear walkthrough for someone starting with zero context: signup → key → first call. We use **curl + Bash** because it's universal — but every example translates directly to any OpenAI- or Anthropic-compatible SDK by changing `baseURL` and leaving everything else alone.

> **Pick a language first if the user has signaled one.** If the user said *"in my Next.js app"* or *"from FastAPI"*, rewrite these steps using the matching SDK before showing them. Don't blindly hand a Bash script to someone integrating from Python.

## What you need

- An AkashML account (free to create).
- A verified email and a payment method on file (unlocks trial credits).
- An API key, stored in `$AKASHML_API_KEY`. **Never paste a literal key inline.**

That's it. No CLI binary, no wallet, no AKT, no SDL.

## Step 1 — Sign up and get an API key

1. Go to [playground.akashml.com](https://playground.akashml.com).
2. Sign up with email; verify your inbox.
3. Add a payment method under **Settings → Billing**. Trial credits unlock once verification + payment-method are both in place.
4. Generate an API key under **Settings → API Keys**. **Copy it immediately** — the plaintext value is shown exactly once. It begins with `akml-`.

## Step 2 — Set the env var

| Where you'll run this | How to set the key |
|---|---|
| **Local shell** (one-off) | `export AKASHML_API_KEY="akml-..."` |
| **Local shell** (persistent) | Add to `~/.zshrc` / `~/.bashrc`, or use `.env` + `direnv` |
| **`.env` file** | `AKASHML_API_KEY=akml-...`; **add `.env` to `.gitignore` immediately** |
| **GitHub Actions** | Settings → Secrets → New secret `AKASHML_API_KEY`; reference as `${{ secrets.AKASHML_API_KEY }}` |
| **Docker** | `docker run -e AKASHML_API_KEY=$AKASHML_API_KEY ...` — runtime only, never `ARG`/`ENV` |

Verify with `echo "${AKASHML_API_KEY:+set}"` — should print `set` without echoing the value.

## Step 3 — List available models

```bash
curl https://api.akashml.com/v1/models \
  -H "Authorization: Bearer $AKASHML_API_KEY" \
  | jq '.data[].id'
```

You'll see a list of open-source model IDs (DeepSeek, Kimi, MiniMax, Qwen, etc.). Pick one and pin it in the next call.

## Step 4 — Your first inference call

The OpenAI surface is the simplest — drop-in compatible with anything that already speaks OpenAI.

```bash
MODEL="MiniMaxAI/MiniMax-M2.5"  # use whatever the list showed

curl -X POST https://api.akashml.com/v1/chat/completions \
  -H "Authorization: Bearer $AKASHML_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -nc --arg model "$MODEL" '{
    model: $model,
    messages: [
      {role: "system", content: "You are a concise assistant."},
      {role: "user", content: "What is Akash Network in one sentence?"}
    ],
    max_completion_tokens: 200
  }')" \
  | jq -r '.choices[0].message.content'
```

If you get a sentence back, you're done — AkashML is wired up. The response carries an `Inference-Id` header you can capture for support requests; not needed for normal use.

## Step 5 — Switch to your SDK

The whole point of the OpenAI/Anthropic-compatible shape: keep your existing client, change one line.

**Python (`openai`):**

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["AKASHML_API_KEY"],
    base_url="https://api.akashml.com/v1",
)

print(client.chat.completions.create(
    model="MiniMaxAI/MiniMax-M2.5",
    messages=[{"role": "user", "content": "Hi from Python."}],
).choices[0].message.content)
```

**Node (`openai`):**

```typescript
import OpenAI from "openai";

const client = new OpenAI({
  apiKey: process.env.AKASHML_API_KEY,
  baseURL: "https://api.akashml.com/v1",
});

const r = await client.chat.completions.create({
  model: "MiniMaxAI/MiniMax-M2.5",
  messages: [{ role: "user", content: "Hi from Node." }],
});
console.log(r.choices[0].message.content);
```

**Python (`anthropic`):**

```python
import os
from anthropic import Anthropic

client = Anthropic(
    api_key=os.environ["AKASHML_API_KEY"],
    base_url="https://api.akashml.com/anthropic",
)

response = client.messages.create(
    model="MiniMaxAI/MiniMax-M2.5",  # both surfaces accept the slashed form
    max_tokens=256,
    messages=[{"role": "user", "content": "Hi from anthropic-py."}],
)
print(response.content[0].text)
```

See [@api-reference.md](api-reference.md) for the full endpoint surface, including streaming, tool use, and the Anthropic-surface specifics.

## What you didn't have to do

- Install any binary
- Write SDL
- Acquire AKT or burn to ACT
- Manage a wallet, mnemonic, or hardware key
- Wait for bids or accept leases
- Deal with `uact` / `uakt` denoms

If a step in your workflow ever requires one of those, you're trying to *host* a model instead of *call* one — and you want [@../../sdl/examples/gpu-workload.md](../../sdl/examples/gpu-workload.md) plus one of the four deployment methods, not AkashML.

## Common pitfalls

| Symptom | Likely cause | Fix |
|---|---|---|
| `401 Unauthorized` | Used `x-api-key` instead of `Authorization: Bearer` | Switch headers — AkashML uses Bearer, not `x-api-key` |
| `401 Unauthorized` | Used a Console API key (`AKASH_API_KEY`) | They're different platforms. Get an `akml-...` key from playground.akashml.com |
| `402 Payment Required` | Out of credits (or trial credits never unlocked) | Verify email + add payment method; top up if you've exhausted credits |
| `404` from Claude Code-shaped client | Slashed model ID rejected client-side | Use the `--` aliased form (`MiniMaxAI--MiniMax-M2.5`); the API itself accepts both |
| `429` Too Many Requests | Hit per-key RPM/TPM/concurrent ceiling | Honor `Retry-After` / `X-RateLimit-Reset`; raise the limit in the dashboard if persistent |
| Hangs forever | Default SDK timeout too low | Raise client timeout for long generations |

## Where to go next

- **[@api-reference.md](api-reference.md)** — Full OpenAI + Anthropic endpoint reference
- **[@authentication.md](authentication.md)** — Key management, rotation, CI/CD wiring
- **[@account-and-billing.md](account-and-billing.md)** — How credits work, auto-top-up, rate limits
- **[@claude-code-integration.md](claude-code-integration.md)** — Use AkashML as the backend for Claude Code itself
