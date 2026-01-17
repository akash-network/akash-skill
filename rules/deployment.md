# Deployment Configuration

The `deployment` section maps services to placement profiles, specifying where and how many instances to run.

## Basic Structure

```yaml
deployment:
  <service-name>:
    <placement-name>:
      profile: <compute-profile-name>
      count: <instance-count>
```

## Deployment Properties

### profile (required)

References a compute profile defined in `profiles.compute`:

```yaml
profiles:
  compute:
    web-profile:
      resources:
        cpu:
          units: 1
        memory:
          size: 1Gi
        storage:
          size: 5Gi

deployment:
  web:
    dcloud:
      profile: web-profile    # References 'web-profile' from profiles.compute
      count: 1
```

### count (required)

Number of instances to deploy (minimum 1):

```yaml
deployment:
  web:
    dcloud:
      profile: web
      count: 3    # Deploy 3 instances
```

## Matching Rules

1. **Service name** must exist in `services` section
2. **Placement name** must exist in `profiles.placement` section
3. **Profile name** must exist in `profiles.compute` section
4. **Pricing** must be defined in the placement for the referenced profile

## Single Service Example

```yaml
version: "2.0"

services:
  web:
    image: nginx:latest
    expose:
      - port: 80
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
  web:                    # Matches 'web' in services
    dcloud:               # Matches 'dcloud' in profiles.placement
      profile: web        # Matches 'web' in profiles.compute
      count: 1
```

## Multi-Service Example

```yaml
version: "2.0"

services:
  frontend:
    image: myapp/frontend:latest
    expose:
      - port: 80
        to:
          - global: true

  backend:
    image: myapp/backend:latest
    expose:
      - port: 8080
        to:
          - service: frontend

  database:
    image: postgres:15
    expose:
      - port: 5432
        to:
          - service: backend

profiles:
  compute:
    frontend-profile:
      resources:
        cpu:
          units: 0.5
        memory:
          size: 512Mi
        storage:
          size: 1Gi

    backend-profile:
      resources:
        cpu:
          units: 1
        memory:
          size: 1Gi
        storage:
          size: 5Gi

    db-profile:
      resources:
        cpu:
          units: 2
        memory:
          size: 2Gi
        storage:
          - name: default
            size: 1Gi
          - name: data
            size: 20Gi
            attributes:
              persistent: true
              class: beta2

  placement:
    dcloud:
      pricing:
        frontend-profile:
          denom: uakt
          amount: 500
        backend-profile:
          denom: uakt
          amount: 1000
        db-profile:
          denom: uakt
          amount: 2000

deployment:
  frontend:
    dcloud:
      profile: frontend-profile
      count: 2              # 2 frontend instances

  backend:
    dcloud:
      profile: backend-profile
      count: 3              # 3 backend instances

  database:
    dcloud:
      profile: db-profile
      count: 1              # 1 database instance
```

## Multiple Placements

Deploy to different placements:

```yaml
profiles:
  placement:
    us-region:
      attributes:
        region: us-west
      pricing:
        web:
          denom: uakt
          amount: 1000

    eu-region:
      attributes:
        region: eu-central
      pricing:
        web:
          denom: uakt
          amount: 1200

deployment:
  web:
    us-region:
      profile: web
      count: 2

    eu-region:
      profile: web
      count: 1
```

## Scaling Considerations

- Each placement can have different instance counts
- Higher counts require more resources and higher pricing budget
- Database services typically use `count: 1` unless using replication
- Stateless services (web, API) can scale horizontally with higher counts
