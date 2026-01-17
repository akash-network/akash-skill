# Example: WordPress with Database

A multi-service deployment with WordPress and MariaDB, featuring persistent storage.

## Use Case

- Content management systems
- Multi-tier applications
- Applications requiring databases
- Persistent data storage

## SDL Configuration

```yaml
version: "2.0"

services:
  wordpress:
    image: wordpress:latest
    env:
      - "WORDPRESS_DB_HOST=db"
      - "WORDPRESS_DB_USER=wordpress"
      - "WORDPRESS_DB_PASSWORD=wordpress_password"
      - "WORDPRESS_DB_NAME=wordpress"
    expose:
      - port: 80
        as: 80
        to:
          - global: true
    params:
      storage:
        wordpress-data:
          mount: /var/www/html
          readOnly: false

  db:
    image: mariadb:10.11
    env:
      - "MYSQL_ROOT_PASSWORD=root_password"
      - "MYSQL_DATABASE=wordpress"
      - "MYSQL_USER=wordpress"
      - "MYSQL_PASSWORD=wordpress_password"
    expose:
      - port: 3306
        to:
          - service: wordpress
    params:
      storage:
        db-data:
          mount: /var/lib/mysql
          readOnly: false

profiles:
  compute:
    wordpress:
      resources:
        cpu:
          units: 1
        memory:
          size: 1Gi
        storage:
          - name: default
            size: 1Gi
          - name: wordpress-data
            size: 10Gi
            attributes:
              persistent: true
              class: beta2

    db:
      resources:
        cpu:
          units: 1
        memory:
          size: 1Gi
        storage:
          - name: default
            size: 1Gi
          - name: db-data
            size: 20Gi
            attributes:
              persistent: true
              class: beta2

  placement:
    dcloud:
      pricing:
        wordpress:
          denom: uakt
          amount: 2000
        db:
          denom: uakt
          amount: 3000

deployment:
  wordpress:
    dcloud:
      profile: wordpress
      count: 1

  db:
    dcloud:
      profile: db
      count: 1
```

## Key Concepts

### Service Communication

Services communicate using service names as hostnames:
- WordPress connects to `db:3306`
- The `db` service is only exposed to `wordpress` service

### Persistent Storage

Both services use persistent storage:
- WordPress content: `/var/www/html`
- Database files: `/var/lib/mysql`

Storage configuration:
```yaml
storage:
  - name: db-data
    size: 20Gi
    attributes:
      persistent: true    # Data survives restarts
      class: beta2        # SSD storage
```

### Storage Mounting

Connect named storage to container paths:
```yaml
params:
  storage:
    db-data:
      mount: /var/lib/mysql
      readOnly: false
```

## Variations

### With Redis Cache

```yaml
version: "2.0"

services:
  wordpress:
    image: wordpress:latest
    env:
      - "WORDPRESS_DB_HOST=db"
      - "WORDPRESS_DB_USER=wordpress"
      - "WORDPRESS_DB_PASSWORD=wordpress_password"
      - "WORDPRESS_DB_NAME=wordpress"
    expose:
      - port: 80
        as: 80
        to:
          - global: true
    params:
      storage:
        wordpress-data:
          mount: /var/www/html

  db:
    image: mariadb:10.11
    env:
      - "MYSQL_ROOT_PASSWORD=root_password"
      - "MYSQL_DATABASE=wordpress"
      - "MYSQL_USER=wordpress"
      - "MYSQL_PASSWORD=wordpress_password"
    expose:
      - port: 3306
        to:
          - service: wordpress
    params:
      storage:
        db-data:
          mount: /var/lib/mysql

  redis:
    image: redis:7-alpine
    expose:
      - port: 6379
        to:
          - service: wordpress

profiles:
  compute:
    wordpress:
      resources:
        cpu:
          units: 1
        memory:
          size: 1Gi
        storage:
          - name: default
            size: 1Gi
          - name: wordpress-data
            size: 10Gi
            attributes:
              persistent: true
              class: beta2

    db:
      resources:
        cpu:
          units: 1
        memory:
          size: 1Gi
        storage:
          - name: default
            size: 1Gi
          - name: db-data
            size: 20Gi
            attributes:
              persistent: true
              class: beta2

    redis:
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
        wordpress:
          denom: uakt
          amount: 2000
        db:
          denom: uakt
          amount: 3000
        redis:
          denom: uakt
          amount: 1000

deployment:
  wordpress:
    dcloud:
      profile: wordpress
      count: 1
  db:
    dcloud:
      profile: db
      count: 1
  redis:
    dcloud:
      profile: redis
      count: 1
```

### PostgreSQL Variant

```yaml
version: "2.0"

services:
  app:
    image: myapp:latest
    env:
      - "DATABASE_URL=postgres://appuser:apppassword@db:5432/appdb"
    expose:
      - port: 3000
        as: 80
        to:
          - global: true

  db:
    image: postgres:15
    env:
      - "POSTGRES_USER=appuser"
      - "POSTGRES_PASSWORD=apppassword"
      - "POSTGRES_DB=appdb"
    expose:
      - port: 5432
        to:
          - service: app
    params:
      storage:
        pgdata:
          mount: /var/lib/postgresql/data

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

    db:
      resources:
        cpu:
          units: 2
        memory:
          size: 2Gi
        storage:
          - name: default
            size: 1Gi
          - name: pgdata
            size: 50Gi
            attributes:
              persistent: true
              class: beta2

  placement:
    dcloud:
      pricing:
        app:
          denom: uakt
          amount: 2000
        db:
          denom: uakt
          amount: 4000

deployment:
  app:
    dcloud:
      profile: app
      count: 1
  db:
    dcloud:
      profile: db
      count: 1
```

## Best Practices

1. **Never expose databases globally**: Use `to: - service: <name>` pattern
2. **Use strong passwords**: Even in examples, use secure password patterns
3. **Size storage appropriately**: Databases grow; allocate sufficient space
4. **Use SSD storage**: `class: beta2` for database workloads
5. **Separate compute profiles**: Different resources for app vs database tiers
