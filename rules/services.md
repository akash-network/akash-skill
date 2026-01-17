# Services Configuration

The `services` section defines the containers and workloads to deploy.

## Basic Service Definition

```yaml
services:
  <service-name>:
    image: <container-image>
    expose:
      - port: <port>
        to:
          - global: true
```

## Service Properties

### image (required)

The container image to deploy:

```yaml
services:
  web:
    image: nginx:latest
```

### command (optional)

Override the container's default command:

```yaml
services:
  app:
    image: node:18
    command:
      - "node"
      - "server.js"
```

### args (optional)

Arguments passed to the command:

```yaml
services:
  app:
    image: myapp:latest
    args:
      - "--config"
      - "/etc/config.yaml"
```

### env (optional)

Environment variables as an array of strings:

```yaml
services:
  app:
    image: myapp:latest
    env:
      - "NODE_ENV=production"
      - "DATABASE_URL=postgres://user:pass@db:5432/mydb"
      - "SECRET_KEY=mysecretkey"
```

### expose (required for accessible services)

Port exposure configuration:

```yaml
services:
  web:
    image: nginx:latest
    expose:
      - port: 80        # Container port (1-65535)
        as: 80          # External port (optional, defaults to port)
        proto: tcp      # Protocol: tcp (default) or udp
        to:
          - global: true    # Expose to internet
```

#### Expose Options

| Field | Type | Description |
|-------|------|-------------|
| `port` | integer | Container port (1-65535, required) |
| `as` | integer | External port (1-65535, optional) |
| `proto` | string | Protocol: `tcp` (default) or `udp` |
| `to` | array | Exposure targets |

#### Exposure Targets

```yaml
expose:
  - port: 80
    to:
      - global: true          # Internet accessible

  - port: 5432
    to:
      - service: web          # Only accessible by 'web' service

  - port: 8080
    to:
      - ip: myendpoint        # Expose via IP endpoint (requires v2.1)
```

#### HTTP Options

For HTTP services, additional options are available:

```yaml
expose:
  - port: 80
    as: 80
    to:
      - global: true
    http_options:
      max_body_size: 1048576      # Max request body (bytes, 0-104857600)
      read_timeout: 60000         # Read timeout (ms, 0-60000)
      send_timeout: 60000         # Send timeout (ms, 0-60000)
      next_tries: 3               # Retry attempts
      next_timeout: 0             # Retry timeout (ms)
      next_cases:                 # Retry conditions
        - error
        - timeout
```

### credentials (optional)

For private container registries:

```yaml
services:
  app:
    image: registry.example.com/myapp:latest
    credentials:
      host: registry.example.com
      username: myuser
      password: mypassword
```

### params (optional)

Storage mount configuration:

```yaml
services:
  db:
    image: postgres:15
    params:
      storage:
        data:
          mount: /var/lib/postgresql/data
          readOnly: false
```

The storage name (`data` in the example) must match a named storage volume in the compute profile.

## Service-to-Service Communication

Services can communicate using their service names as hostnames:

```yaml
services:
  web:
    image: nginx:latest
    env:
      - "API_URL=http://api:3000"
    expose:
      - port: 80
        to:
          - global: true

  api:
    image: myapi:latest
    expose:
      - port: 3000
        to:
          - service: web    # Only web can access
```

## Complete Example

```yaml
services:
  frontend:
    image: myapp/frontend:v1.0
    env:
      - "API_URL=http://backend:8080"
    expose:
      - port: 3000
        as: 80
        to:
          - global: true
        http_options:
          max_body_size: 5242880

  backend:
    image: myapp/backend:v1.0
    command:
      - "node"
      - "server.js"
    env:
      - "DATABASE_URL=postgres://postgres:password@db:5432/myapp"
      - "NODE_ENV=production"
    expose:
      - port: 8080
        to:
          - service: frontend

  db:
    image: postgres:15
    env:
      - "POSTGRES_PASSWORD=password"
      - "POSTGRES_DB=myapp"
    expose:
      - port: 5432
        to:
          - service: backend
    params:
      storage:
        pgdata:
          mount: /var/lib/postgresql/data
```
