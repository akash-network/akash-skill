# AkashML Account and Billing

AkashML billing is a **USD credit balance** on your AkashML account. It is **not** on-chain — there is no `uact` / `uakt` involvement on this path. AkashML pays the underlying providers on your behalf out of your credit balance.

This is structurally different from every other path in this skill. Anchor on the table below before reading the rest.

| Path | What you fund | Denom of record | Where the money goes |
|---|---|---|---|
| **AkashML** | AkashML credits (USD) | USD (off-chain) | AkashML pays inference providers |
| **Console API** | Console managed wallet (USD via Stripe) | USD → `uact` on-chain | Lease escrow for *your* deployment |
| **CLI / SDK** | Self-custody wallet (AKT, then burn → ACT) | `uakt` (gas) + `uact` (escrow) | Lease escrow for *your* deployment |

If you're already thinking about "deposit", "escrow", "uact", "burn rate", or "lease balance", you're on the wrong path — those concepts belong to deploying your own workload, not calling AkashML. See [@overview.md](overview.md) "When to use AkashML vs alternatives" if you're unsure which path you want.

## Funding the account

1. Sign up at [playground.akashml.com](https://playground.akashml.com) and verify your email.
2. Under **Settings → Billing**, add a payment method (Stripe). This unlocks **trial credits** on the account.
3. Top up manually as needed, or enable **auto-top-up** at a configured threshold.

### Auto-top-up

The dashboard lets you set:

- A **threshold** (e.g., $5) below which the account auto-charges your saved payment method.
- A **top-up amount** (e.g., $25) that gets added when the threshold trips.

This is dashboard-only configuration — there is no observed programmatic endpoint for managing billing settings. For automation that needs guaranteed availability, keep the threshold conservatively high and monitor usage.

### Credit expiration

- **Trial credits expire** — granted on email verify + payment method, with an expiration date attached.
- **Purchased credits do not expire.**

Plan around this: if you let an account go idle long enough, only the purchased balance remains. Always read the live balance from the dashboard rather than caching the "I bought $X last month" mental model.

## Reading usage and balance

Usage and remaining balance are surfaced in the **AkashML dashboard**. There is no documented programmatic balance endpoint at the time of writing — if you need to gate behavior on remaining credit from code, treat the dashboard as the source of truth and rely on `429` responses to back-pressure your client.

If a balance endpoint exists in a future release, it will be added here.

## Per-key limits

Each API key has independently configurable limits (set in the dashboard, not via API):

| Limit | Meaning | What happens when exceeded |
|---|---|---|
| **RPM** | Requests per minute | `429 Too Many Requests` |
| **TPM** | Tokens per minute (input + output combined) | `429 Too Many Requests` |
| **Concurrent** | Simultaneous in-flight requests | `429 Too Many Requests` |
| **Expiration** | Optional ISO 8601 date | Key stops working after this date |

The limits are per-key, so you can split workloads across keys to isolate noisy producers from latency-sensitive consumers.

## Two failure modes: out of credits vs rate limited

Treat these distinctly — the fixes differ.

| Status | Meaning | Headers to inspect | Fix |
|---|---|---|---|
| `402 Payment Required` | **Out of credits** on the account (not a per-key limit) | — | Top up the account, or enable auto-top-up. Retrying without topping up will keep failing. |
| `429 Too Many Requests` | Per-key rate limit (RPM/TPM/concurrent) | `Retry-After`, `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` | Honor `Retry-After`; back off. Raise the limit in the dashboard if it's a persistent ceiling. |

`402` is **not** retryable on its own — your client must either short-circuit, fall back to a different account, or surface the error to a human. Retrying a `402` in a tight loop just wastes the next request.

## Handling `429` with the right headers

```typescript
async function callWithBackoff(fn: () => Promise<Response>, maxRetries = 5) {
  let delay = 1000;
  for (let i = 0; i < maxRetries; i++) {
    const response = await fn();
    if (response.status === 402) {
      throw new Error("Out of AkashML credits — top up the account");
    }
    if (response.status !== 429) return response;

    const retryAfter = parseInt(response.headers.get("Retry-After") ?? "0", 10);
    const reset = parseInt(response.headers.get("X-RateLimit-Reset") ?? "0", 10);
    const computedDelay = retryAfter
      ? retryAfter * 1000
      : reset
        ? Math.max(reset * 1000 - Date.now(), 0)
        : delay;

    await new Promise((r) => setTimeout(r, computedDelay));
    delay = Math.min(delay * 2, 30_000);
  }
  throw new Error("Rate limited after retries");
}
```

Order of preference: `Retry-After` → `X-RateLimit-Reset` → exponential backoff with jitter.

## Stripe-specific notes

AkashML's billing relationship is with **AkashML**, not with the Akash chain. Stripe charges show up under the AkashML account. There is no token movement on-chain triggered by your AkashML usage — the chain-side economics of the underlying providers are handled by AkashML internally.

This means:

- **No AKT / ACT acquisition needed.** AkashML users never touch the Akash chain.
- **No `uact` deposit visible in your account.** Your balance is denominated in USD credits.
- **No lease lifecycle to manage.** AkashML owns the underlying deployments; you only interact with the inference API.

If you want chain-side visibility (lease balances, escrow burn rate, on-chain auditability), you want one of the four deployment paths, not AkashML.

## Cost shape

Pricing is **per-token**, varying by model. The dashboard displays current rates for each model. Pricing details are intentionally not enumerated here because they shift faster than this file does — always check the dashboard or the model's listing in the API response for live pricing.

For cost-sensitive workloads, the same trade-offs as any inference API apply:

- Cache frequent prompts client-side.
- Use shorter `max_tokens` and stricter `system` prompts.
- Pick smaller models for simple tasks; reserve large models for harder requests.
- Stream responses to reduce perceived latency without changing token cost.

## Related files

- **[@overview.md](overview.md)** — Path comparison and when AkashML is the wrong answer
- **[@authentication.md](authentication.md)** — Per-key limit semantics, env vars, rotation
- **[@api-reference.md](api-reference.md)** — `429` handling in context of the API surface
