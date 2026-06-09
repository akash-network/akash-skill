# Example: Resource Reclamation

SDL configuration declaring a minimum reclamation grace window (AEP-82).

## Use Case

- Stateful workloads that need lead time to drain or snapshot before a provider reclaims resources
- Migrations where you must move to another lease before the current one is closed
- Any deployment that should not be reclaimed without a guaranteed notice period

## Version Requirement

The `reclamation` block requires SDL version 2.1:

```yaml
version: "2.1"
```

SDL "2.0" still works unchanged — reclamation is opt-in.

## Basic Reclamation Window

```yaml
version: "2.1"

reclamation:
  min_window: "24h"

services:
  web:
    image: nginx:1.25.3
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
          units: 1
        memory:
          size: 1Gi
        storage:
          size: 5Gi

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

## Stateful Service with a Longer Window

A database that needs time to flush and snapshot before reclamation requests a
multi-day window (still within the 720h governance maximum):

```yaml
version: "2.1"

reclamation:
  min_window: "72h"

services:
  db:
    image: postgres:16.2
    env:
      - "POSTGRES_PASSWORD=changeme"
    expose:
      - port: 5432
        to:
          - global: false
    params:
      storage:
        data:
          mount: /var/lib/postgresql/data

profiles:
  compute:
    db:
      resources:
        cpu:
          units: 2
        memory:
          size: 4Gi
        storage:
          - name: default
            size: 1Gi
          - name: data
            size: 100Gi
            attributes:
              persistent: true
              class: beta2

  placement:
    dcloud:
      pricing:
        db:
          denom: uact
          amount: 5000

deployment:
  db:
    dcloud:
      profile: db
      count: 1
```

## Notes

1. **Bounds:** `min_window` must be a positive Go duration within `[1h, 720h]`.
2. **Bidding:** providers that cannot honor a window at least as long as your
   `min_window` will not bid — a very long window may reduce available bids.
3. **Lifecycle:** see [../../deploy/cli/deployment-lifecycle.md](../../deploy/cli/deployment-lifecycle.md)
   for the `Active → Reclaiming → paused group` flow.
4. **Compatibility:** requires node v2.1.0 / provider-services v0.13.0+. Omitting the
   block keeps full SDL 2.0 behavior.
