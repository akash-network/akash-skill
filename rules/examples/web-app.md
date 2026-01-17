# Example: Simple Web Application

A minimal SDL for deploying a web application on Akash.

## Use Case

- Static websites
- Single-page applications
- Simple API servers
- Development/testing environments

## SDL Configuration

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

## Variations

### Node.js Application

```yaml
version: "2.0"

services:
  app:
    image: node:18-alpine
    command:
      - "node"
      - "server.js"
    env:
      - "NODE_ENV=production"
      - "PORT=3000"
    expose:
      - port: 3000
        as: 80
        to:
          - global: true

profiles:
  compute:
    app:
      resources:
        cpu:
          units: 1
        memory:
          size: 1Gi
        storage:
          size: 2Gi
  placement:
    dcloud:
      pricing:
        app:
          denom: uakt
          amount: 1500

deployment:
  app:
    dcloud:
      profile: app
      count: 1
```

### Python Flask Application

```yaml
version: "2.0"

services:
  api:
    image: python:3.11-slim
    command:
      - "python"
      - "-m"
      - "flask"
      - "run"
      - "--host=0.0.0.0"
    env:
      - "FLASK_APP=app.py"
      - "FLASK_ENV=production"
    expose:
      - port: 5000
        as: 80
        to:
          - global: true

profiles:
  compute:
    api:
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
        api:
          denom: uakt
          amount: 1000

deployment:
  api:
    dcloud:
      profile: api
      count: 1
```

### Custom Docker Image

```yaml
version: "2.0"

services:
  myapp:
    image: myregistry/myapp:v1.0.0
    credentials:
      host: myregistry.io
      username: ${REGISTRY_USER}
      password: ${REGISTRY_PASS}
    env:
      - "DATABASE_URL=postgres://..."
      - "API_KEY=${API_KEY}"
    expose:
      - port: 8080
        as: 80
        to:
          - global: true
        http_options:
          max_body_size: 10485760
          read_timeout: 30000

profiles:
  compute:
    myapp:
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
        myapp:
          denom: uakt
          amount: 2000

deployment:
  myapp:
    dcloud:
      profile: myapp
      count: 2
```

## Resource Guidelines

| Application Type | CPU | Memory | Storage |
|-----------------|-----|--------|---------|
| Static site | 0.25-0.5 | 256-512Mi | 512Mi-1Gi |
| Node.js app | 0.5-2 | 512Mi-2Gi | 1-5Gi |
| Python app | 0.5-2 | 512Mi-2Gi | 1-5Gi |
| Go app | 0.25-1 | 128-512Mi | 512Mi-2Gi |

## Tips

1. **Start small**: Begin with minimal resources and scale up as needed
2. **Use specific tags**: Avoid `latest` in production; use specific version tags
3. **Environment variables**: Use env vars for configuration, never hardcode secrets
4. **HTTP options**: Configure timeouts based on your application's needs
5. **Multiple instances**: Set `count: 2` or higher for high availability
