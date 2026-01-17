# SDL Validation Rules

This document lists all constraints and validation rules for Akash SDL configurations.

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
| `next_tries` | 0-10 | 3 |
| `next_timeout` | 0-60000 ms | 0 |

```yaml
# Valid
http_options:
  max_body_size: 52428800     # 50MB
  read_timeout: 30000         # 30 seconds

# Invalid
http_options:
  max_body_size: 200000000    # Error: exceeds 100MB limit
  read_timeout: 120000        # Error: exceeds 60000ms limit
```

## Pricing Constraints

| Field | Valid Values |
|-------|--------------|
| `denom` | `uakt` or `ibc/...` pattern |
| `amount` | Positive integer |

```yaml
# Valid - Native AKT
pricing:
  web:
    denom: uakt
    amount: 1000

# Valid - USDC via IBC
pricing:
  web:
    denom: ibc/170C677610AC31DF0904FFE09CD3B5C657492170E7E52372E48756B71E56F2F1
    amount: 100

# Invalid
pricing:
  web:
    denom: usdc       # Error: must be 'uakt' or 'ibc/...'
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

## Reference Constraints

### Service Names

Services in `deployment` must exist in `services`:

```yaml
services:
  web:
    image: nginx:latest

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
          denom: uakt
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
          denom: uakt
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
| Port range | 1-65535 |
| Timeout range | 0-60000ms |
| Body size | 0-104857600 bytes (100MB) |
| Price denom | `uakt` or `ibc/...` pattern |
| Price amount | Positive integer |
| RAM storage | Cannot be persistent |
| Non-RAM + attributes | Requires persistent=true |
| GPU with units > 0 | Must have attributes with vendor |
| GPU with units = 0 | Cannot have attributes |
| Endpoints | Must be global, must be used, requires v2.1 |
| Deployment count | Minimum 1 |
| References | All names must match across sections |
