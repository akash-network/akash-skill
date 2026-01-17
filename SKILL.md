---
name: akash-sdl
description: Generate valid Akash Network SDL configurations for deploying containers on the decentralized cloud. Use when asked to "create Akash deployment", "generate SDL", "deploy to Akash", or "Akash config".
license: MIT
metadata:
  author: baktun14
  version: "1.0.0"
  argument-hint: <deployment-description>
---

# Akash SDL Generator

Generate valid Akash Network Stack Definition Language (SDL) configurations for deploying containerized applications on the decentralized cloud.

## SDL Structure Overview

Every SDL file has four required sections:

```yaml
version: "2.0"  # or "2.1" for IP endpoints

services:       # Container definitions
profiles:       # Compute resources & placement
deployment:     # Service-to-profile mapping
```

Optional section for IP endpoints:
```yaml
endpoints:      # IP lease endpoints (requires version 2.1)
```

## Quick Reference

### Minimal SDL Template

```yaml
version: "2.0"

services:
  web:
    image: nginx:latest
    expose:
      - port: 80
        as: 80
        to:
          - global: true

profiles:
  compute:
    web:
      resources:
        cpu:
          units: 0.5
        memory:
          size: 512Mi
        storage:
          size: 1Gi
  placement:
    dcloud:
      pricing:
        web:
          denom: uakt
          amount: 1000

deployment:
  web:
    dcloud:
      profile: web
      count: 1
```

## Detailed Rules

For complete configuration options, see the rules directory:

- **@schema-overview.md** - Version requirements and SDL structure
- **@services.md** - Service configuration (image, expose, env, credentials)
- **@compute-resources.md** - CPU, memory, storage, and GPU specifications
- **@placement-pricing.md** - Provider selection and pricing configuration
- **@deployment.md** - Service-to-profile deployment mapping
- **@endpoints.md** - IP endpoint configuration (v2.1)
- **@validation-rules.md** - All constraints and validation rules

## Examples

See the examples directory for complete working configurations:

- **@examples/web-app.md** - Simple web deployment
- **@examples/wordpress-db.md** - Multi-service with persistent storage
- **@examples/gpu-workload.md** - GPU deployment with NVIDIA
- **@examples/ip-lease.md** - IP endpoint configuration

For 100+ production-ready templates, see [awesome-akash](https://github.com/akash-network/awesome-akash).

## Common Patterns

### Environment Variables
```yaml
services:
  app:
    env:
      - "DATABASE_URL=postgres://..."
      - "NODE_ENV=production"
```

### Persistent Storage
```yaml
profiles:
  compute:
    app:
      resources:
        storage:
          - size: 10Gi
            attributes:
              persistent: true
              class: beta2
```

### GPU Workloads
```yaml
profiles:
  compute:
    ml:
      resources:
        gpu:
          units: 1
          attributes:
            vendor:
              nvidia:
                - model: a100
```

### Payment Options
- **uakt**: Native Akash Token (e.g., `amount: 1000`)
- **USDC**: Via IBC denom (e.g., `denom: ibc/170C677610AC31DF0904FFE09CD3B5C657492170E7E52372E48756B71E56F2F1`)

## Additional Resources

- **[awesome-akash](https://github.com/akash-network/awesome-akash)** - Community-curated library of production-ready SDL templates for databases, AI/ML, gaming, web apps, and more
- **[chain-sdk](https://github.com/akash-network/chain-sdk/tree/main/ts/src/sdl)** - Official SDL schema and validation reference
