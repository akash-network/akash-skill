# Bid Matching

Diagnose why an Akash SDL isn't getting bids — or predict whether it will — by matching its compute requirements against the live audited + online provider set returned by `https://console-api.akash.network/v1/providers`.

This is the live-market companion to the SDL syntax/validation rules under `rules/sdl/`. Schema validity says the SDL *parses*; bid matching says the SDL *can land on a real provider right now*.

## When to use this

Trigger this workflow whenever a user:

- Asks "why am I not getting bids" / "will this SDL get bids" / "which providers can run this"
- Pastes an SDL and wants a feasibility check before broadcasting
- Plans a GPU or otherwise large deployment and wants to verify supply
- Reports an empty or stuck bid list on Console
- Asks to "adapt", "fix", or "optimize" an SDL for better bid coverage

Pair with the SDL rules: those tell you if the YAML is valid; this tells you if the network actually has a provider that can run it.

## How it works

1. Fetch `https://console-api.akash.network/v1/providers`.
2. Keep only providers where `isOnline === true` AND `isAudited === true`. Both filters matter — offline providers won't bid at all, and audited providers are what Console surfaces by default.
3. Extract compute requirements from every profile in the SDL (CPU millis, memory, ephemeral + persistent storage, storage class, GPU count + vendor + model, IP endpoint need).
4. Check each provider's `stats.*.available` and capability flags against those requirements.
5. Produce a funnel that shows which single constraint collapses the provider pool. The biggest filter is usually more useful than the final count, because it tells the user what to relax.

## Running the matcher

The repo ships `scripts/match_providers.py`. Given an SDL file path, it fetches live providers and prints a JSON report:

```bash
python3 scripts/match_providers.py /path/to/deploy.yaml
```

Optional flags:
- `--top N` — top N matching providers per profile (default 5)
- `--api URL` — override the providers endpoint
- `--json` — emit only JSON (default behavior anyway)

If the user pasted an SDL inline, save it to a temp file first:

```bash
TMP=$(mktemp -t sdl).yaml
cat > "$TMP" <<'EOF'
<paste SDL here>
EOF
python3 scripts/match_providers.py "$TMP"
```

Requires `pyyaml`. Install with `pip3 install --user pyyaml` (or use a venv).

## Interpreting the report

The script returns JSON like:

```json
{
  "total_providers": 60,
  "online_providers": 34,
  "online_audited_providers": 22,
  "profiles": [
    {
      "profile": "sglang",
      "requirements": { ... },
      "funnel": [
        {"stage": "total_providers", "count": 60},
        {"stage": "online", "count": 34},
        {"stage": "online_audited", "count": 22},
        {"stage": "passes_cpu", "count": 8, "applicable": true},
        {"stage": "passes_memory", "count": 6, "applicable": true},
        {"stage": "passes_gpu_model", "count": 0, "applicable": true}
      ],
      "biggest_filter": "passes_gpu_model",
      "match_count": 0,
      "feasible": false
    }
  ]
}
```

**The most important field is `biggest_filter`.** It names the single constraint that the fewest providers pass. That's the lever to pull first to widen the pool.

Each `passes_<check>` stage has an `applicable` flag — checks that don't apply to this profile (e.g., `passes_gpu_model` when the profile has no GPU) should be ignored.

## How to present results

Every response must include both the diagnosis **and** a complete adapted SDL — even if the verdict is "feasible" (in which case the adapted SDL is identical to the input, noted as such). The user wants a copy-pasteable file, not snippets to hand-merge.

Structure:

1. **One-line feasibility verdict** — "X of Y online+audited providers can satisfy profile `<name>`." If zero, say so plainly.
2. **Funnel** — show the dropoff stage by stage. A compact table works well. Highlight the biggest filter.
3. **Requirement summary** — what the profile asks for (human-readable: "96 cores, 512 GiB RAM, 8× nvidia/h200, 800 GiB persistent beta3").
4. **Top matching providers** (if any) — name, region, GPUs. Don't dump all fields.
5. **Changes made** — tight bullet list naming every field being modified and why, ordered by impact. One line per change.
6. **Full adapted SDL** — a single fenced ```yaml``` block containing the entire adapted document, not a diff or partial snippet. Preserve the user's original keys, comments, ordering, and structure except where deliberately changing things.
7. **Caveats** — anything the report can't verify. See "Known limitations" below.

The full SDL is required on every invocation; never skip it with "here are the changes, apply them to your file." If the SDL already matches enough providers and no change is warranted, output the original SDL verbatim under step 6 and say "no changes needed" in step 5.

When picking changes:

- Work from the biggest filter outward — don't relax things that aren't filtering.
- Never silently change semantics (drop a persistent volume the app needs, remove an IP endpoint the service depends on). If a relaxation would break the app, say so in step 5 and skip it rather than applying it.
- If the user's app intent is ambiguous (e.g., can the workload fit on fewer GPUs?), make the conservative choice (keep the count) and mention the alternative for them to opt into.
- Preserve the input's version, image tags, env vars, command/args, and anything else untouched. Do not reformat or restyle YAML.

## Known limitations

- **Denom support is not in the providers endpoint.** The script accepts `uact` and IBC denoms as recognized. It can't verify which denoms a *specific* provider accepts — that's invisible.
- **Per-GPU-model availability is not exposed.** The endpoint reports total GPU count via `stats.gpu.available` and a list of models via `gpuModels[]`, but not a per-model available count. The matcher treats "provider has this model in `gpuModels` AND total GPUs available ≥ requested" as a match — it can overcount when one provider has mixed models.
- **Provider-side bid config (floor prices, deployment ACLs, denom acceptance) is not exposed.** A provider can satisfy the SDL on paper and still decline the bid based on its own pricing rules or policy. The report predicts *capability*, not *intent*.
- **Stats are snapshots.** Available capacity changes minute-to-minute as leases come and go.

Surface these caveats when they matter — especially when the verdict is "feasible" but the user is still not getting bids. At that point SDL changes are the wrong lever; recommend out-of-band actions (direct provider DM on Akash Discord, smaller-model functional test, pre-arranged capacity).

## Adaptation rules

See `rules/bid-matching/adaptation-rules.md` for the priority order of changes (what to change, what to leave alone, why).

For the underlying SDL ↔ provider field mapping, unit conversions, and edge cases, see `rules/bid-matching/matching-rules.md`.
