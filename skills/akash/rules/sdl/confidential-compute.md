# SDL Confidential Compute / TEE (`params.tee`)

A tenant requests a **Confidential Compute (TEE)** workload by setting a single
field — `tee` — under a service's `params`. This is the SDL surface of AEP-83
(Confidential Compute via Kata Containers).

Confidential compute is **opt-in** and needs **no SDL version bump**: `params.tee`
works with `version: "2.0"`, and a deployment that omits the field behaves exactly
as before.

## The field

```yaml
services:
  web:
    image: nginx:1.25.3
    expose:
      - port: 80
        to:
          - global: true
    params:
      tee: cpu
```

`tee` is a plain string that lives under `services.<name>.params`, alongside the
existing `storage` mounts. It takes one of two values:

| Value | Meaning |
|-------|---------|
| `cpu` | CPU-only confidential compute. The provider selects the underlying TEE platform (AMD SEV-SNP or Intel TDX). |
| `cpu-gpu` | CPU **+** GPU confidential compute. Requires GPU resources in the compute profile (see below). |

## What the tenant does *not* set

TEE deployments are deliberately simple on the tenant side:

- **No attestation toggle.** The provider injects an attestation sidecar into every
  confidential workload automatically — there is no SDL field to enable or disable it.
- **No hardware / platform choice.** You request a *capability* (`cpu` or
  `cpu-gpu`), not a specific chip. The provider picks the confidential-compute
  hardware (AMD SEV-SNP vs Intel TDX) and the matching runtime at deploy time.

There is exactly one control — the `tee` string. Everything else (runtime class,
platform detection, attestation) is handled provider-side.

## `cpu-gpu` requires GPU resources

The `cpu-gpu` value requires the service's compute profile to declare `gpu`
resources. An SDL that sets `tee: cpu-gpu` without a GPU in the profile is
**rejected** at validation time. See the GPU section of
[compute-resources.md](compute-resources.md) for GPU profile syntax.

## Same value across a deployment group

All services in the same deployment group must use the **same** `tee` value, or
none of them may set it. Mixing TEE values (or mixing TEE and non-TEE services)
within a single group is rejected. See [validation-rules.md](validation-rules.md).

## Examples

### CPU-only confidential compute

```yaml
version: "2.0"

services:
  web:
    image: nginx:1.25.3
    expose:
      - port: 80
        to:
          - global: true
    params:
      tee: cpu

profiles:
  compute:
    web:
      resources:
        cpu:
          units: 2
        memory:
          size: 2Gi
        storage:
          size: 10Gi
  placement:
    dcloud:
      pricing:
        web:
          denom: uact
          amount: 1000

deployment:
  web:
    dcloud:
      profile: web
      count: 1
```

### CPU + GPU confidential compute

```yaml
version: "2.0"

services:
  inference:
    image: nvidia/cuda:12.0-runtime-ubuntu22.04
    expose:
      - port: 8080
        to:
          - global: true
    params:
      tee: cpu-gpu

profiles:
  compute:
    inference:
      resources:
        cpu:
          units: 8
        memory:
          size: 32Gi
        storage:
          size: 100Gi
        gpu:
          units: 1
          attributes:
            vendor:
              nvidia:
                - model: h100
  placement:
    dcloud:
      pricing:
        inference:
          denom: uact
          amount: 5000

deployment:
  inference:
    dcloud:
      profile: inference
      count: 1
```

See [examples/confidential-compute.md](examples/confidential-compute.md) for the
full annotated examples.

## Marketplace matching

Setting `tee` requires no extra placement configuration from the tenant. The SDL
builder automatically projects a `tee/type = <value>` placement attribute, and the
marketplace uses it to match your order with providers that advertise the requested
confidential-compute capability. Providers without TEE support (or without the
requested `cpu` / `cpu-gpu` capability) simply will not bid.

## Validation

- `tee` must be `cpu` or `cpu-gpu`.
- `cpu-gpu` requires GPU resources in the compute profile.
- All services in a deployment group must use the same value or none.

See [validation-rules.md](validation-rules.md) for the constraint reference.
