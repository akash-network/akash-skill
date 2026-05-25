# Using AkashML as the Backend for Claude Code

Because the AkashML Anthropic-compatible surface speaks the Anthropic Messages API, you can point Claude Code itself at AkashML by setting two environment variables. Claude Code will then route its requests to open-source models running on Akash compute instead of (or alongside) Anthropic's first-party API.

This file documents that integration specifically. For the generic Anthropic API surface (any client), see [@api-reference.md](api-reference.md).

> Caveat: open-source models behind the Anthropic-compatible surface are not Anthropic's Claude models. Capability, latency, and tool-use compliance differ. Treat this as a separate backend with its own characteristics, not a drop-in for first-party Claude.

## Required env vars

| Variable | Value | Purpose |
|---|---|---|
| `ANTHROPIC_BASE_URL` | `https://api.akashml.com/anthropic` | Redirect Claude Code's Anthropic client to AkashML |
| `ANTHROPIC_AUTH_TOKEN` | `akml-...` (your AkashML key) | Auth credential (Bearer-style) |

## Optional model mappings

Claude Code asks for `sonnet`/`opus`/`haiku` tiers internally. Map each tier to a concrete AkashML model so requests resolve to the right open-source model:

| Variable | Suggested model (verify against `/anthropic/v1/models`) | Why |
|---|---|---|
| `ANTHROPIC_DEFAULT_SONNET_MODEL` | `deepseek-ai/DeepSeek-V4-Flash` | Fast general-purpose coding model |
| `ANTHROPIC_DEFAULT_OPUS_MODEL` | `moonshotai/Kimi-K2.6` | Larger reasoning-focused model for harder tasks |
| `ANTHROPIC_DEFAULT_HAIKU_MODEL` | `Qwen/Qwen3.5-35B-A3B` | Lightweight for quick lookups |

These values match the AkashML guide. Use the slashed (canonical) form here even though `GET /anthropic/v1/models` returns IDs in the `--` form — the env vars are interpreted by Claude Code before the API call, and Claude Code accepts the slashed AkashML model IDs as documented.

> **Always verify with the live API before pinning.** Run `curl -H "Authorization: Bearer $AKASHML_API_KEY" https://api.akashml.com/v1/models | jq '.data[] | {id, context_length, pricing, supported_features}'` and pick models whose `context_length`, `supported_features` (tools, streaming, reasoning), and `pricing` match your needs. The four IDs above are starting suggestions, not commitments — the AkashML catalog and their recommended mappings change.

## Configuring on macOS / Linux

Add an `env` block to `~/.claude/settings.json`:

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://api.akashml.com/anthropic",
    "ANTHROPIC_AUTH_TOKEN": "akml-...",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "deepseek-ai/DeepSeek-V4-Flash",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "moonshotai/Kimi-K2.6",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "Qwen/Qwen3.5-35B-A3B",
    "API_TIMEOUT_MS": "3000000"
  }
}
```

`API_TIMEOUT_MS` raises Claude Code's per-call timeout. Agentic loops with open-source models can run long; 3,000,000 ms (50 minutes) is what the AkashML docs recommend. Lower it if your workflows are short.

> Reminder: do not commit `~/.claude/settings.json` with the literal key. Either keep the key out of the file and export it as a shell env var (Claude Code reads ambient env vars too), or commit a template with a placeholder and document the export step.

## Configuring on Windows

PowerShell (persistent, user scope):

```powershell
[System.Environment]::SetEnvironmentVariable("ANTHROPIC_BASE_URL", "https://api.akashml.com/anthropic", "User")
[System.Environment]::SetEnvironmentVariable("ANTHROPIC_AUTH_TOKEN", "akml-...", "User")
[System.Environment]::SetEnvironmentVariable("ANTHROPIC_DEFAULT_SONNET_MODEL", "deepseek-ai/DeepSeek-V4-Flash", "User")
[System.Environment]::SetEnvironmentVariable("ANTHROPIC_DEFAULT_OPUS_MODEL", "moonshotai/Kimi-K2.6", "User")
[System.Environment]::SetEnvironmentVariable("ANTHROPIC_DEFAULT_HAIKU_MODEL", "Qwen/Qwen3.5-35B-A3B", "User")
[System.Environment]::SetEnvironmentVariable("API_TIMEOUT_MS", "3000000", "User")
```

Command Prompt (`setx`):

```cmd
setx ANTHROPIC_BASE_URL "https://api.akashml.com/anthropic"
setx ANTHROPIC_AUTH_TOKEN "akml-..."
setx ANTHROPIC_DEFAULT_SONNET_MODEL "deepseek-ai/DeepSeek-V4-Flash"
setx ANTHROPIC_DEFAULT_OPUS_MODEL "moonshotai/Kimi-K2.6"
setx ANTHROPIC_DEFAULT_HAIKU_MODEL "Qwen/Qwen3.5-35B-A3B"
setx API_TIMEOUT_MS "3000000"
```

After `setx`, open a new terminal — `setx` writes to the registry but doesn't update the current process.

## Verifying the redirect

After setting the env vars, start a fresh Claude Code session and make a tiny request (e.g. *"say hi"*). Quick checks:

- Inference latency feels different from first-party Claude (varies by model and provider).
- The AkashML dashboard shows usage tick up.
- Token charges land on the AkashML account, not Anthropic billing.

If usage doesn't appear in the AkashML dashboard, the redirect isn't active — Claude Code probably fell back to first-party Anthropic. Re-check the env vars are present in the process Claude Code actually launched from (a parent shell, `~/.claude/settings.json`, etc.).

## What this changes — and what it doesn't

**Changes:**

- Where requests go (AkashML, not `api.anthropic.com`).
- Who pays (your AkashML credits, not your Anthropic account).
- What model actually runs (open-source on Akash compute).

**Doesn't change:**

- Claude Code's own CLI surface, tool calls, file edits, etc.
- Local files on disk (this is purely a backend redirect).
- Anthropic-specific features Claude Code uses (tool use, system prompts, streaming) — *to the extent the chosen open-source model supports them*. Some models will degrade silently on advanced features.

## Caveats

- **Tool-use parity is not guaranteed.** Open-source models vary widely in how well they follow Anthropic's tool-use schema. Test on real tasks before relying on it for production workflows.
- **Context windows vary.** Each underlying model has its own context limit; Claude Code doesn't know about per-model limits beyond what the API returns. Expect `400` on overlong inputs.
- **No prompt caching guarantees.** AkashML may not implement Anthropic's prompt-cache headers identically. Don't assume cache savings transfer.

## Why this is the most useful integration to document

For most consumers of the Anthropic-compatible surface, generic SDK docs ([@api-reference.md](api-reference.md)) are enough. Claude Code is the exception because the env-var contract is non-obvious, the model-mapping variables are Claude-Code-specific, and the timeout knob matters for agentic workflows in ways stateless inference doesn't surface.

## Related files

- **[@api-reference.md](api-reference.md)** — Generic Anthropic surface (any client)
- **[@authentication.md](authentication.md)** — Key creation, the `akml-` prefix, env-var rules
- **[@account-and-billing.md](account-and-billing.md)** — Credits and per-key limits that apply to Claude Code sessions too
