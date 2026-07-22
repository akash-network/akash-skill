# SDL Validation Rules

This document lists all constraints and validation rules for Akash SDL configurations.

## Image Tag Constraints

**Docker images must specify an explicit tag.** The `latest` tag is not allowed.

```yaml
# Valid - explicit version tag
services:
  web:
    image: nginx:1.25.3

# Valid - semantic version
services:
  app:
    image: node:18-alpine

# Valid - SHA digest
services:
  api:
    image: myapp@sha256:abc123...

# Invalid - latest tag
services:
  web:
    image: nginx:latest    # Error: 'latest' tag not allowed

# Invalid - no tag (implies latest)
services:
  web:
    image: nginx           # Error: must specify explicit tag
```

**Why?** The `latest` tag is mutable and can change unexpectedly, causing deployment inconsistencies. Explicit tags ensure reproducible deployments.

## Port Constraints

| Field | Valid Range | Notes |
|-------|-------------|-------|
| `port` | 1-65535 | Container port |
| `as` | 1-65535 | External port (optional) |

```yaml
# Valid
expose:
  - port: 80
    as: 8080

# Invalid - port out of range
expose:
  - port: 0       # Error: must be >= 1
  - port: 70000   # Error: must be <= 65535
```

## HTTP Options Constraints

| Field | Valid Range | Default |
|-------|-------------|---------|
| `max_body_size` | 0-104857600 (100MB) | 1048576 (1MB) |
| `read_timeout` | 0-60000 ms | 60000 |
| `send_timeout` | 0-60000 ms | 60000 |
| `next_tries` | Not range-validated | 3 |
| `next_timeout` | Not range-validated | 0 |
| `next_cases` | Array of strings | `["error", "timeout"]` |

> Only `read_timeout` and `send_timeout` are range-capped (0-60000 ms) by the SDL parser. `next_timeout` and `next_tries` are not range-validated.

```yaml
# Valid
http_options:
  max_body_size: 52428800     # 50MB
  read_timeout: 30000         # 30 seconds
  next_cases:
    - error
    - timeout
    - "502"                   # HTTP status codes must be quoted strings
    - "503"
    - "504"

# Invalid
http_options:
  max_body_size: 200000000    # Error: exceeds 100MB limit
  read_timeout: 120000        # Error: exceeds 60000ms limit
  next_cases:
    - 502                     # Error: numbers must be quoted as strings
    - 503
```

## Pricing Constraints

| Field | Valid Values |
|-------|--------------|
| `denom` | `uact` (the SDL pricing denom) |
| `amount` | Positive integer |

```yaml
# Valid - ACT (deployment-payment token)
pricing:
  web:
    denom: uact
    amount: 1000

# Invalid
pricing:
  web:
    denom: usdc       # Error: must be 'uact'
    amount: -100      # Error: must be positive
```

## Storage Constraints

### RAM Storage

RAM-based storage cannot be persistent:

```yaml
# Valid
storage:
  - name: cache
    size: 1Gi
    attributes:
      class: ram
      persistent: false

# Invalid
storage:
  - name: cache
    size: 1Gi
    attributes:
      class: ram
      persistent: true    # Error: RAM cannot be persistent
```

### Non-RAM Storage with Attributes

Non-RAM storage classes with attributes must be persistent:

```yaml
# Valid
storage:
  - name: data
    size: 10Gi
    attributes:
      class: beta2
      persistent: true

# Invalid
storage:
  - name: data
    size: 10Gi
    attributes:
      class: beta2
      persistent: false   # Error: non-RAM with class must be persistent
```

### Simple Storage (No Constraints)

Storage without attributes has no special constraints:

```yaml
# Valid - ephemeral storage
storage:
  size: 5Gi

# Valid - named ephemeral
storage:
  - name: default
    size: 5Gi
```

## GPU Constraints

### GPU with units > 0

Must have attributes with vendor specified:

```yaml
# Valid
gpu:
  units: 1
  attributes:
    vendor:
      nvidia:

# Valid - with model
gpu:
  units: 2
  attributes:
    vendor:
      nvidia:
        - model: a100

# Invalid - missing attributes
gpu:
  units: 1              # Error: must have attributes with vendor

# Invalid - missing vendor
gpu:
  units: 1
  attributes: {}        # Error: must specify vendor
```

### GPU with units = 0

Cannot have attributes:

```yaml
# Valid
gpu:
  units: 0

# Invalid
gpu:
  units: 0
  attributes:           # Error: cannot have attributes when units=0
    vendor:
      nvidia:
```

## Confidential Compute (TEE) Constraints

The `services.<name>.params.tee` field (AEP-83) has three constraints.

### Allowed Values

`tee` must be `cpu` or `cpu-gpu`:

```yaml
# Valid - CPU-only confidential compute
services:
  web:
    params:
      tee: cpu

# Valid - CPU + GPU confidential compute
services:
  inference:
    params:
      tee: cpu-gpu

# Invalid - unknown value
services:
  web:
    params:
      tee: sev          # Error: must be 'cpu' or 'cpu-gpu'
```

### cpu-gpu Requires GPU Resources

`tee: cpu-gpu` requires the compute profile to declare GPU resources:

```yaml
# Valid - cpu-gpu with a GPU in the profile
services:
  inference:
    params:
      tee: cpu-gpu
profiles:
  compute:
    inference:
      resources:
        gpu:
          units: 1
          attributes:
            vendor:
              nvidia:

# Invalid - cpu-gpu without GPU resources
services:
  inference:
    params:
      tee: cpu-gpu      # Error: cpu-gpu requires GPU resources in the profile
profiles:
  compute:
    inference:
      resources:
        cpu:
          units: 4
```

### Same Value Per Deployment Group

All services in a deployment group must use the same `tee` value, or none:

```yaml
# Valid - both services request the same TEE value
services:
  web:
    params:
      tee: cpu
  api:
    params:
      tee: cpu

# Invalid - mixed TEE values in one group
services:
  web:
    params:
      tee: cpu
  api:
    params:
      tee: cpu-gpu      # Error: all services in a group must use the same value or none
```

See [confidential-compute.md](confidential-compute.md) for the full field reference.

## Endpoint Constraints

### Must Be Global

IP endpoints implicitly expose services globally:

```yaml
# Valid
expose:
  - port: 80
    to:
      - ip: myendpoint

# The endpoint exposure is global by nature
```

### Must Be Used

Declared endpoints must be referenced:

```yaml
# Invalid - unused endpoint
endpoints:
  myip:
    kind: ip            # Error: endpoint declared but not used

services:
  web:
    expose:
      - port: 80
        to:
          - global: true    # Does not reference 'myip'
```

### Version Requirement

IP endpoints require version 2.1:

```yaml
# Valid
version: "2.1"
endpoints:
  myip:
    kind: ip

# Invalid
version: "2.0"          # Error: endpoints require version 2.1
endpoints:
  myip:
    kind: ip
```

## Reclamation Constraints

The optional `reclamation` block (AEP-82) requires version 2.1 and a valid window.

### Window Bounds

`min_window` must be a positive Go duration within the governance bounds
`[min_reclamation_window, max_reclamation_window]` — defaults **1h–720h**:

```yaml
# Valid
version: "2.1"
reclamation:
  min_window: "24h"

# Invalid - below minimum
reclamation:
  min_window: "10m"     # Error: below min_reclamation_window (1h)

# Invalid - above maximum
reclamation:
  min_window: "1000h"   # Error: above max_reclamation_window (720h)

# Invalid - not a positive duration
reclamation:
  min_window: "0s"      # Error: must be positive
```

### Version Requirement

The `reclamation` block requires version 2.1:

```yaml
# Invalid
version: "2.0"          # Error: reclamation requires version 2.1
reclamation:
  min_window: "24h"
```

See [reclamation.md](reclamation.md) for the full field reference.

## Reference Constraints

### Service Names

Services in `deployment` must exist in `services`:

```yaml
services:
  web:
    image: nginx:1.25.3

deployment:
  web:                  # Valid: matches 'web' in services
    dcloud:
      profile: web
      count: 1
  api:                  # Error: 'api' not defined in services
    dcloud:
      profile: api
      count: 1
```

### Dependencies

Service dependencies must reference existing services:

```yaml
services:
  api:
    image: myapp:v1.0.0
    dependencies:
      - service: database    # Valid: 'database' exists
      - service: cache       # Error if 'cache' not defined

  database:
    image: postgres:15
```

Circular dependencies should be avoided to prevent startup deadlocks.

### Profile Names

Profiles in `deployment` must exist in `profiles.compute`:

```yaml
profiles:
  compute:
    web:
      resources:
        cpu:
          units: 1

deployment:
  web:
    dcloud:
      profile: web      # Valid: matches 'web' in profiles.compute
      count: 1
  api:
    dcloud:
      profile: api      # Error: 'api' not in profiles.compute
      count: 1
```

### Placement Names

Placements in `deployment` must exist in `profiles.placement`:

```yaml
profiles:
  placement:
    dcloud:
      pricing:
        web:
          denom: uact
          amount: 1000

deployment:
  web:
    dcloud:             # Valid: matches 'dcloud' in profiles.placement
      profile: web
      count: 1
    other:              # Error: 'other' not in profiles.placement
      profile: web
      count: 1
```

### Pricing Coverage

Placements must have pricing for all profiles used:

```yaml
profiles:
  compute:
    web:
      resources: ...
    api:
      resources: ...
  placement:
    dcloud:
      pricing:
        web:
          denom: uact
          amount: 1000
        # Missing: api pricing

deployment:
  web:
    dcloud:
      profile: web
      count: 1
  api:
    dcloud:
      profile: api      # Error: no pricing for 'api' in 'dcloud'
      count: 1
```

## Deployment Constraints

| Field | Constraint |
|-------|------------|
| `count` | Must be >= 1 |

```yaml
# Valid
deployment:
  web:
    dcloud:
      profile: web
      count: 1

# Invalid
deployment:
  web:
    dcloud:
      profile: web
      count: 0          # Error: count must be at least 1
```

## Summary Table

| Constraint | Rule |
|------------|------|
| Image tag | Must be explicit, `latest` not allowed |
| Port range | 1-65535 |
| Timeout range | 0-60000ms |
| Body size | 0-104857600 bytes (100MB) |
| next_cases | All values must be strings (quote HTTP status codes) |
| Price denom | `uact` (the SDL pricing denom) |
| Price amount | Positive integer |
| RAM storage | Cannot be persistent |
| Non-RAM + attributes | Requires persistent=true |
| GPU with units > 0 | Must have attributes with vendor |
| GPU with units = 0 | Cannot have attributes |
| TEE value | Must be `cpu` or `cpu-gpu` |
| TEE `cpu-gpu` | Requires GPU resources in the profile |
| TEE per group | All services same value or none |
| Endpoints | Must be global, must be used, requires v2.1 |
| Reclamation `min_window` | Positive Go duration within 1h–720h, requires v2.1 |
| Deployment count | Minimum 1 |
| Dependencies | Must reference existing services |
| References | All names must match across sections |
