# SDL Resource Reclamation (`reclamation`)

The optional top-level `reclamation` block lets a tenant declare the **minimum grace
window** a provider must honor before it may reclaim the lease's resources. This is
the SDL surface of AEP-82 Resource Reclamation.

Requires SDL version `"2.1"`. SDL `"2.0"` continues to work unchanged — reclamation
is **opt-in**; omit the block and leases behave exactly as before.

## The block

```yaml
version: "2.1"
reclamation:
  min_window: "24h"
```

| Field | Type | Required | Meaning |
|-------|------|----------|---------|
| `min_window` | Go duration string (e.g. `"1h"`, `"24h"`, `"720h"`) | Yes, when the block is present | Minimum time a provider must wait after starting reclamation before it may close the lease. Must be positive. |

The value maps to `DeploymentReclamation` (field 5 on `MsgCreateDeployment`). When the
block is omitted the field is nil and the deployment carries no reclamation
requirement.

## Governance bounds

`min_window` must fall within the market's governance parameters:

- **Minimum:** `1h` (param `min_reclamation_window`, default 1h)
- **Maximum:** `720h` / 30 days (param `max_reclamation_window`, default 720h)

A `min_window` outside `[1h, 720h]` is rejected at validation time. See
[validation-rules.md](validation-rules.md).

## When to use

Set a `reclamation` requirement when your workload needs guaranteed lead time to
react before a provider can reclaim its resources — for example to drain
connections, snapshot state, or migrate to another lease. Providers that cannot
honor a window at least as long as your `min_window` will not bid.

## What happens at runtime

Declaring `min_window` does not change normal operation. It only constrains
provider-initiated reclamation: once a provider starts reclamation, it cannot close
the lease until the window elapses. See the full lifecycle —
[deployment-lifecycle.md](../deploy/cli/deployment-lifecycle.md) — for the
`Active → Reclaiming → paused group` flow and recovery via `MsgStartGroup`.

## Client requirements

Resource reclamation requires the v2.1.0-compatible toolchain:

- **Node:** v2.1.0 (mainnet upgrade)
- **Provider:** provider-services v0.13.0 or later (the build paired with node v2.1.0)
- **chain-sdk:** `@akashnetwork/chain-sdk@alpha` (TS) / `pkg.akt.dev/go` (Go)

Pre-2.1 nodes do not understand the field; detect support via the discovery endpoint
(`node_version >= 2.1.0`) before submitting — see
[sdk/overview.md](../sdk/overview.md).
