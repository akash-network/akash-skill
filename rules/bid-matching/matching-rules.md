# SDL ↔ Provider Field Mapping

Reference for how the matcher maps SDL compute requirements to provider capability fields returned by `https://console-api.akash.network/v1/providers`.

The matcher is a *forecast* of what the actual provider bid engine in [akash-network/provider](https://github.com/akash-network/provider) will accept. Where the underlying logic differs from a naive pool-wide check, this doc cites the canonical file:line in the provider repo so the matcher's behavior can be verified against ground truth. **Caveat up front:** the providers endpoint reports pool-wide totals (CPU/memory/GPU/storage `available`) per provider; the actual bid engine works *per node* (each replica must fit on a single node, all GPUs of a service on one node). The matcher is therefore optimistic for multi-replica or large single-node GPU asks.

## Filter: which providers to consider

| Provider field | Required value | Why |
|----------------|----------------|-----|
| `isOnline` | `true` | Offline providers don't respond to bid requests at all. |
| `isAudited` | `true` | Console and most tooling surfaces audited providers by default; unaudited providers exist but are not the pool most deployments land on. |

Both filters are applied up front before any capability checks. The funnel reports the dropoff at each stage.

## CPU

- **SDL:** `resources.cpu.units` — accepts `0.5`, `2`, or `"500m"` (millicores)
- **Provider:** `stats.cpu.available` — reported in millicores
- **Match:** `stats.cpu.available >= requested_millis * deployment.count`

The script multiplies per-service requirements by `deployment[svc][placement].count` because a single provider typically has to fit all replicas.

**Canonical:** `tryAdjust` does CPU via `SubMilliNLZ` per-node (`provider/cluster/kube/operators/clients/inventory/inventory.go:46`), then `Adjust` walks nodes one at a time decrementing `resources[i].Count` per fit (`inventory.go:243-294`). Overcommit factors (`CPUCommitLevel`/`MemoryCommitLevel`/`GPUCommitLevel`) are applied via `sdlutil.ComputeCommittedResources` *before* `Adjust`, scaling the requested amount down by the commit ratio (`provider/cluster/inventory.go:286-294`). The matcher does not model overcommit — its check is conservative for that reason but optimistic on per-node fit.

## Memory

- **SDL:** `resources.memory.size` — accepts `Ki`/`Mi`/`Gi`/`Ti` (binary) and `k`/`M`/`G`/`T` (decimal)
- **Provider:** `stats.memory.available` — bytes
- **Match:** `stats.memory.available >= requested_bytes * count`

## Storage

SDL storage can be a single object (`size: 5Gi`) or an array of named volumes with attributes.

### Ephemeral

- **SDL:** storage entries without `attributes.persistent: true`
- **Provider:** `stats.storage.ephemeral.available`
- **Match:** sum of ephemeral requests ≤ available

### Persistent

- **SDL:** storage entries with `attributes.persistent: true` and a `class` (e.g., `beta2`, `beta3`)
- **Provider capacity:** `stats.storage.persistent.available` (bytes)
- **Provider class support:** derived from the `attributes[]` array, which declares pairs of:
  - `capabilities/storage/<N>/class = <beta1|beta2|beta3|ram|...>`
  - `capabilities/storage/<N>/persistent = true|false`

  A class counts as persistent-capable when the matching slot's `persistent` is `true`. The older `feat-persistent-storage-type=<class>` attribute is also honored as a fallback.
- **Match:** capacity sufficient AND the requested class is in the provider's set of persistent-capable classes.

Do **not** use `featPersistentStorageType` to match SDL classes — that field uses hardware taxonomy (`hdd`, `ssd`, `nvme`), not Akash's SDL class taxonomy (`beta1`, `beta2`, `beta3`). They are unrelated.

The providers endpoint does not break down persistent capacity by class, so total persistent availability is the only capacity check available — class support is verified via the attribute pairs above.

### RAM-class volumes

RAM-class storage (`class: ram`) is ephemeral by definition. The current matcher treats it as ephemeral capacity. Not all providers expose RAM-class volumes, but this endpoint doesn't explicitly report that — be aware the match can be optimistic for RAM volumes.

## GPU

- **SDL:** `resources.gpu.units` + `resources.gpu.attributes.vendor.<vendor>[{ model, ram, interface }]`. Each entry under `vendor.<v>[*]` is an *alternative* — any one of them being satisfied is a pass.
- **Provider:** `stats.gpu.available` (count, total across all models on the cluster), `gpuModels[]` (array of `{ vendor, model, ram, interface }`).
- **Match:**
  - `stats.gpu.available >= units * count`, AND
  - For each SDL alternative, the provider's `gpuModels` contains at least one entry matching every field that was specified — vendor (always required), `model` (case-insensitive), `ram` (string-equal, e.g. `"80Gi"`), `interface` (case-insensitive). The matcher tracks all four fields, not just model.

**Canonical:** `tryAdjustGPU` (`provider/cluster/kube/operators/clients/inventory/inventory.go:125-203`) iterates `rp.Info[]` (each entry is one discrete GPU) and decrements `reqCnt` only when vendor + model + optional RAM + interface all match. `cinventory.ParseGPUAttributes` resolves SDL keys like `vendor/nvidia/model/h100/ram/80Gi/interface/sxm5`. Wildcards: `*` is supported on the model field via `ExistsOrWildcard`.

### GPU matching caveats

- `stats.gpu.available` is not broken down by model. A provider with 4× A100 free and 4× H100 leased reports `available: 4` total — but the matcher treats "provider has the model in `gpuModels` AND total available ≥ requested" as a pass. **A provider with mixed GPU models can be overcounted** if some of those models are leased while the unrequested ones are free.
- The provider bid engine fits all GPUs of a service on a *single node*. The Console API exposes per-provider totals only — `stats.gpu.available: 8` could be 4 free on each of two nodes, which would not satisfy an `8× h200` ask. The matcher cannot detect this from the API.
- Rare models (H200, B200, MI300X) appear in very few providers' `gpuModels`. The biggest-filter analysis surfaces this automatically.
- For multi-model fallback, the user can declare multiple entries under `vendor.nvidia:` — the matcher considers any match a pass (mirrors `provider/.../inventory.go:tryAdjustGPU` outer loop).

## Placement attributes

- **SDL:** `profiles.placement.<name>.attributes` (a key=value map; e.g. `region: us-west`, `host: akash`, `tier: enterprise`)
- **Provider:** `attributes[]` array on the provider, with each entry `{ key, value, auditedBy[] }`
- **Match:** every required `key=value` from the SDL must be present on the provider, with **glob-aware** value comparison in either direction (provider-side or SDL-side wildcards work).

**Canonical:** `bidengine/order.go:shouldBid` (lines 523-594) calls `MatchAttributes` (`chain-sdk/.../v1beta4/groupspec.go:108-146`) which uses `Attributes.SubsetOf` with `filepath.Match`-based key matching (`chain-sdk/.../attributes/v1/attribute.go:104-219`). The provider's *own* declared attributes (e.g. `host=akash`, `region=us-west`, `capabilities/gpu=...`) must be a superset of the SDL's required attributes.

The matcher implements glob matching via Python `fnmatch.fnmatchcase` in both directions to mirror the `filepath.Match` glob semantics (limited — `*` matches any characters, `?` matches one).

## IP endpoints

- **SDL v2.1 trigger:** a service's `expose[*].to[*]` contains `{ ip: <name> }`, or the top-level `endpoints:` block declares one
- **Provider:** `featEndpointIp === true` (Console-API derived field)
- **Match:** required iff the SDL uses an IP endpoint

**Canonical:** the provider has no specific feat-key check for IP support; instead it tracks IP allocation in cluster inventory (`provider/cluster/inventory.go:432-447`) and rejects with `errInsufficientIPs` when no addresses are free. The matcher uses Console's `featEndpointIp` boolean as a heuristic since the per-IP-quota count isn't exposed.

## Pricing / denom

After the BME rollout, **`uact` (ACT) is the primary denom** on Akash; `uakt` still works as a fallback, and USDC is supported via its IBC denom. The providers endpoint does **not** expose which denominations a provider accepts, so denom support can't be verified from this data.

The matcher treats `uakt`, `uact`, and any `ibc/[A-F0-9]{64}` denom as recognized (no warning). Anything else gets a note that it's unrecognized. Do **not** advise switching denoms to "fix bids" — in practice the bottleneck is almost always GPU model/count/storage class, not denom.

**Canonical chain check:** `x/market/handler/server.go:66` — when a provider posts a bid, the chain rejects with `ErrBidInvalidPrice` ("invalid bid price") if `order.Price().IsLT(msg.Price)`, i.e. the provider's bid exceeds the SDL's stated max amount. The Console UI surfaces this as *"Unit price exceeds the maximum allowed by the network"* (mapped in `console/apps/api/src/billing/services/chain-error/chain-error.service.ts`). Raising `pricing.<profile>.amount` can also trip this from the deployer side depending on how the chain validates `MsgCreateDeployment` — leave it alone.

**Provider-side pricing:** `BidPricingStrategy.CalculatePrice` (`provider/bidengine/pricing.go`) computes the provider's bid; `bidengine/order.go:419-427` rejects on denom mismatch or when the computed price exceeds the SDL ceiling. The matcher cannot see provider-side floor prices — they're a silent gate.

## Unit conversion quick reference

| Input | Parsed as |
|-------|-----------|
| `0.5` (cpu.units) | 500 millicores |
| `2` (cpu.units) | 2000 millicores |
| `"500m"` | 500 millicores |
| `512Mi` | 536,870,912 bytes |
| `2Gi` | 2,147,483,648 bytes |
| `100M` | 100,000,000 bytes |

## Edge cases

- **Missing `count`** — defaults to 1 per placement.
- **Multiple placements for one service** — the matcher uses the pricing/placement pair from each deployment entry; each profile is checked against the union of its usages.
- **Storage name without `class`** — treated as ephemeral with no class constraint.
- **GPU with `units: 0` and attributes** — invalid per SDL rules, ignored by the matcher (no GPU check applied).
- **`gpuModels` empty but `stats.gpu.available > 0`** — provider has GPUs but model is unknown; the model check fails for any model-constrained request.

## Things the matcher cannot see (canonical bid filters not in the providers API)

- **Provider-local attribute allowlist** (`cfg.Attributes` checked in `provider/bidengine/order.go:531`) — provider may require *the deployer's order* to declare specific attributes. Not exposed.
- **MaxGroupVolumes** (`provider/bidengine/config.go`, checked at `order.go:548`) — provider can cap total volume count per group.
- **Per-node fit and overcommit** — see CPU and GPU sections above.
- **`IsStorageClassSupported` cluster check** — even if attributes declare `class=beta3`, the provider's cluster operator does a runtime check (`provider/cluster/kube/.../inventory.go:85-107`) the matcher can't reach.
- **Custom shellscript filter** (`provider/bidengine/shellscript.go`) — providers can run arbitrary scripts to reject orders. Invisible.
- **Existing bid dedupe and stale expiry** (`order.go:255`) — if a bid is already pending, the provider doesn't re-bid.

## Keep in mind

This matcher predicts **capability**, not **intent**. A provider can satisfy the SDL on paper and still decline to bid because of its own price floor, regional policy, or deployment filter. Treat a positive match as "the bid can land here if the provider's price engine agrees," not as a guarantee.
