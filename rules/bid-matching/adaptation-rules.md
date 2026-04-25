# Bid-Matching Adaptation Rules

When adapting an SDL to widen the bid pool, follow this priority order. The order encodes a real lesson: GPU model swaps are tempting because they multiply bidder count fast, but they silently break workloads when the new GPU can't fit the model — bids land, the lease starts ticking, and the container OOMs at startup. Count reductions preserve workload behavior; model swaps don't.

## What to leave alone — pricing and denom

**Never modify `pricing.<profile>.amount` or `pricing.<profile>.denom`.**

- The Akash chain enforces a max bid price. Raising `amount` can trip a *"Unit price exceeds the maximum allowed by the network"* error and the deployment is rejected outright before any bid window opens.
- The providers endpoint does **not** expose which denoms a provider accepts, so denom changes are guesswork. `uact` is the post-BME default; do not reach for `uakt` to "fix" bids.
- Pricing is a deployer choice, not a bid-matching lever. The matcher's job is to align compute requirements (CPU/memory/storage/GPU/feature flags) with provider supply.

If capability matches are tiny and workload-relaxation options are exhausted, recommend out-of-band actions (direct provider DMs on Akash Discord, smaller-model functional test, pre-arranged capacity) — don't reach for the price knob.

## Adaptation priority — try each tier before the next

### 1. Reduce GPU count, keep the requested model

Safest first move. The model the user picked is presumably the one their workload actually runs on; lower count keeps GPU architecture, memory-per-card, and bandwidth identical, so behavior at startup is predictable.

Example: `8× H200 → 4× H200` before considering H100.

If the workload (TP/DP config, model memory footprint) genuinely needs N GPUs, this lever is unavailable — say so explicitly and skip to step 2.

### 2. Add fallback GPU models *of similar or larger memory*

Only after step 1. Order from closest match downward (H200 → H100 → A100). For each model added, sanity-check the workload's memory budget — adding a smaller-memory GPU just trades "no bids" for "bids that OOM at startup," which costs the user real money on the lease before they can close it.

**Never add a model the workload cannot fit.** When unsure of fit, say so and let the user confirm. Quick reference for big LLMs:

| GPUs | Total memory | Fits Kimi-K2 / DeepSeek-V3-class (~1 TB fp8)? |
|------|---:|---|
| 8× H200 (141 GB) | 1128 GB | yes, comfortable |
| 8× H100 (80 GB) | 640 GB | only with fp8 + careful KV cache |
| 8× A100-80GB | 640 GB | tight, may OOM with long context |
| 4× any 80 GB | 320 GB | no |

### 3. Drop the model constraint entirely

Last resort. Use `vendor.nvidia:` with no model list. Only if step 2 still yields nothing and the user has explicitly accepted the OOM/quality risk.

### 4. Storage class

`beta3` is supported by fewer providers than `beta2`. RAM-class volumes require opt-in. Class support is read from `attributes[]` keys `capabilities/storage/<N>/class` (paired with `.../persistent`).

Counter-intuitive case: relaxing `beta3 → beta2` can *reduce* the match count if your workload's GPU model only exists at providers that declare `beta3`. Always re-run the matcher after a class change.

### 5. Persistent storage

If the workload can tolerate ephemeral, skip persistent entirely. Verify the provider has `featPersistentStorage=true` (or attribute `feat-persistent-storage=true`) before assuming a persistent volume will land.

### 6. IP endpoints

`featEndpointIp` is relatively rare; avoid if not essential.

### 7. CPU/memory size

Very large single-node asks (>64 CPU, >256 GiB) narrow the pool. Sizing should follow real workload need; oversized asks filter providers without buying anything.

## When changes are exhausted

If capability matches plateau at 1–2 providers and the workload can't be relaxed further, **say so directly and stop iterating the SDL.** The remaining gates — bid-engine price floors, denom acceptance config, deployment ACLs, stale capacity — aren't visible in the providers endpoint and aren't fixable from the SDL.

Recommend out-of-band actions:
- Direct provider DM on Akash Discord (with a 2-provider pool, a 30-second message beats another deploy cycle).
- Smaller-model functional test on the same SDL shape, to validate plumbing while waiting on capacity.
- Pre-arranged capacity for niche workloads that aren't a walk-up bid today.

## What providers tell us about feature support

Use these fields when deciding whether a provider can satisfy a feature:

| Feature | Where to look |
|---|---|
| Persistent storage at all | top-level `featPersistentStorage`, OR attribute `feat-persistent-storage=true` |
| Specific persistent class (`beta2`/`beta3`) | attributes `capabilities/storage/<N>/class=<cls>` paired with `capabilities/storage/<N>/persistent=true`; fallback `feat-persistent-storage-type=<cls>` |
| RAM-class volumes | attribute `capabilities/storage/<N>/class=ram` |
| IP endpoints | top-level `featEndpointIp` |
| Custom domains | top-level `featEndpointCustomDomain` |
| CPU architecture | `hardwareCpuArch` (`x86-64`, `arm64`) or attribute `capabilities/cpu/arch` |
| GPU vendor/model | `gpuModels[]` with `{vendor, model, ram, interface}` |
| GPU free count (any model) | `stats.gpu.available` |
| Region / location | `locationRegion`, `country`, `ipCountry`, attributes `region`, `location-region` |

`stats.gpu.available` is **not** broken down by model — a provider with mixed GPU types reports a single total. Treat the model match as best-effort and surface that caveat when relevant.

The providers endpoint does **not** expose: accepted denoms, bid-engine price floors, deployment ACLs, or per-model GPU availability. When a deployment capability-matches but gets no bids, those invisible factors are usually the gate.
