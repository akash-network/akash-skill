# SDL Schema Overview

## Version Requirement

The SDL version must be specified as the first field:

```yaml
version: "2.0"
```

Use version `"2.1"` when you need IP endpoints:

```yaml
version: "2.1"
```

## Required Sections

Every valid SDL must contain these four sections:

| Section | Purpose |
|---------|---------|
| `version` | SDL version string |
| `services` | Container and workload definitions |
| `profiles` | Compute resources and placement configuration |
| `deployment` | Maps services to placement profiles |

## Optional Sections

| Section | Purpose | Requires Version |
|---------|---------|------------------|
| `endpoints` | IP lease endpoint declarations | 2.1 |

## Basic Structure

```yaml
version: "2.0"

services:
  <service-name>:
    image: <container-image>
    expose:
      - port: <port>
        to:
          - global: true

profiles:
  compute:
    <profile-name>:
      resources:
        cpu:
          units: <cpu-units>
        memory:
          size: <memory-size>
        storage:
          size: <storage-size>
  placement:
    <placement-name>:
      pricing:
        <profile-name>:
          denom: uakt
          amount: <price>

deployment:
  <service-name>:
    <placement-name>:
      profile: <profile-name>
      count: <instance-count>
```

## Naming Rules

- Service names, profile names, and placement names must be valid identifiers
- Use lowercase letters, numbers, and hyphens
- Names must start with a letter
- Names are case-sensitive

## Section Dependencies

1. **services** - Defines what containers to run
2. **profiles.compute** - Defines resource requirements for each service
3. **profiles.placement** - Defines where to deploy and pricing per compute profile
4. **deployment** - Links services to placements using compute profiles

All service names referenced in `deployment` must exist in `services`.
All profile names referenced in `deployment` must exist in `profiles.compute`.
All placement names used in `deployment` must exist in `profiles.placement`.
