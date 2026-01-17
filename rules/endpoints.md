# IP Endpoints Configuration

IP endpoints allow you to lease dedicated IP addresses for your deployments. This feature requires SDL version 2.1.

## Version Requirement

```yaml
version: "2.1"    # Required for IP endpoints
```

## Basic Structure

### 1. Declare the endpoint

```yaml
endpoints:
  <endpoint-name>:
    kind: ip
```

### 2. Reference in service expose

```yaml
services:
  web:
    expose:
      - port: 80
        to:
          - ip: <endpoint-name>
```

## Complete Example

```yaml
version: "2.1"

services:
  web:
    image: nginx:latest
    expose:
      - port: 80
        as: 80
        to:
          - ip: myip
      - port: 443
        as: 443
        to:
          - ip: myip

endpoints:
  myip:
    kind: ip

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
          denom: uakt
          amount: 1000

deployment:
  web:
    dcloud:
      profile: web
      count: 1
```

## Endpoint Rules

| Rule | Description |
|------|-------------|
| Must be global scope | IP endpoints expose services to the internet |
| Must be used | Declared endpoints must be referenced by at least one service |
| Single kind | Currently only `kind: ip` is supported |
| Version 2.1 | IP endpoints require SDL version "2.1" |

## Multiple Ports on Same IP

You can expose multiple ports through the same IP endpoint:

```yaml
services:
  app:
    image: myapp:latest
    expose:
      - port: 80
        as: 80
        to:
          - ip: public-ip
      - port: 443
        as: 443
        to:
          - ip: public-ip
      - port: 22
        as: 22
        proto: tcp
        to:
          - ip: public-ip

endpoints:
  public-ip:
    kind: ip
```

## Multiple IP Endpoints

You can declare multiple IP endpoints for different services:

```yaml
version: "2.1"

services:
  web:
    image: nginx:latest
    expose:
      - port: 80
        to:
          - ip: web-ip

  api:
    image: myapi:latest
    expose:
      - port: 8080
        as: 80
        to:
          - ip: api-ip

endpoints:
  web-ip:
    kind: ip
  api-ip:
    kind: ip

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
    api:
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
          denom: uakt
          amount: 500
        api:
          denom: uakt
          amount: 1000

deployment:
  web:
    dcloud:
      profile: web
      count: 1
  api:
    dcloud:
      profile: api
      count: 1
```

## Combining Global and IP Exposure

You can expose a service both via the default Akash hostname and a dedicated IP:

```yaml
services:
  web:
    image: nginx:latest
    expose:
      - port: 80
        as: 80
        to:
          - global: true    # Akash-provided hostname
      - port: 80
        as: 8080
        to:
          - ip: dedicated   # Dedicated IP on port 8080

endpoints:
  dedicated:
    kind: ip
```

## When to Use IP Endpoints

| Use Case | Recommendation |
|----------|----------------|
| Standard web apps | Use `global: true` (default hostnames) |
| Custom domains | Use IP endpoint with DNS A record |
| Non-HTTP protocols | Use IP endpoint |
| Multiple ports | Use IP endpoint |
| Gaming servers | Use IP endpoint (UDP support) |
| Email servers | Use IP endpoint |

## Cost Considerations

IP endpoints have additional costs on top of compute resources. The IP lease is billed separately from the deployment pricing. Factor this into your budget when designing deployments.
