# Example: Confidential Compute (TEE)

SDL configurations for Confidential Compute (TEE) workloads (AEP-83). A tenant
requests confidential compute with a single service param — `params.tee` — set to
`cpu` (CPU-only) or `cpu-gpu` (CPU + GPU).

## Use Case

- Workloads processing sensitive data (keys, PII, proprietary models) that must stay
  encrypted in use, not just at rest and in transit
- Confidential AI/ML inference where both the model weights and the input data are
  protected inside a TEE
- Any deployment that needs hardware-backed attestation of the runtime environment

## No Version Bump

`params.tee` works with SDL version `"2.0"` — confidential compute is opt-in and does
not require version `"2.1"`. A deployment that omits `tee` behaves exactly as before.

## CPU-Only Confidential Compute

```yaml
version: "2.0"

services:
  web:
    image: nginx:1.25.3
    expose:
      - port: 80
        as: 80
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

The provider selects the underlying TEE platform (AMD SEV-SNP or Intel TDX) and the
matching Kata runtime automatically — there is nothing else to configure.

## CPU + GPU Confidential Compute

The `cpu-gpu` value **requires** GPU resources in the compute profile. Without a
`gpu` block the SDL is rejected.

```yaml
version: "2.0"

services:
  inference:
    image: nvidia/cuda:12.0-runtime-ubuntu22.04
    command:
      - "python"
      - "serve.py"
    expose:
      - port: 8080
        as: 80
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

## Notes

1. **Two values only:** `tee` must be `cpu` or `cpu-gpu`. No other values are valid.
2. **`cpu-gpu` needs a GPU:** the compute profile must declare `gpu` resources, or the
   SDL is rejected. See [../compute-resources.md](../compute-resources.md).
3. **Same value per group:** all services in a deployment group must use the same
   `tee` value, or none of them. Mixed TEE values in one group are rejected.
4. **Nothing else to set:** attestation is injected by the provider automatically and
   the hardware platform (SEV-SNP vs TDX) is chosen by the provider — there is no
   tenant-facing attestation toggle or platform selector.
5. **Matching:** a `tee/type = <value>` placement attribute is projected
   automatically; providers without the requested capability will not bid.

See [../confidential-compute.md](../confidential-compute.md) for the full reference.
