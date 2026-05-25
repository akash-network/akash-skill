# Storage Classes Reference

Akash Network supports multiple storage classes for different use cases.

## Available Storage Classes

| Class | Type | Persistent | Speed | Use Case |
|-------|------|------------|-------|----------|
| `default` | Ephemeral | No | Fast | Temporary data, caches |
| `beta2` | SSD | Yes | Fast | Databases, general persistent |
| `beta3` | NVMe | Yes | Fastest | High-performance workloads |
| `ram` | RAM Disk | No | Ultra-fast | Caches, temp files |

## Storage Configuration

### Ephemeral Storage (Default)

Data is lost when container restarts:

```yaml
profiles:
  compute:
    web:
      resources:
        storage:
          size: 10Gi
```

### Named Volumes

Multiple volumes with different classes:

```yaml
profiles:
  compute:
    db:
      resources:
        storage:
          - name: default
            size: 1Gi
          - name: data
            size: 50Gi
            attributes:
              persistent: true
              class: beta2
```

### Mounting Volumes

Connect named storage to container paths:

```yaml
services:
  db:
    image: postgres:16
    params:
      storage:
        data:
          mount: /var/lib/postgresql/data
          readOnly: false
```

## Storage Class Details

### beta2 (SSD)

Standard persistent SSD storage:

```yaml
storage:
  - name: data
    size: 100Gi
    attributes:
      persistent: true
      class: beta2
```

**Characteristics:**
- SSD-backed
- Survives container restarts
- Survives provider maintenance
- Good balance of speed and cost

**Best for:**
- Databases (PostgreSQL, MySQL, MongoDB)
- Application data
- File uploads
- General persistence

### beta3 (NVMe)

High-performance NVMe storage:

```yaml
storage:
  - name: fast-data
    size: 100Gi
    attributes:
      persistent: true
      class: beta3
```

**Characteristics:**
- NVMe-backed
- Highest I/O performance
- Lower latency than beta2
- May have limited availability

**Best for:**
- High-IOPS databases
- Real-time analytics
- Performance-critical workloads

### ram (RAM Disk)

Ultra-fast volatile storage:

```yaml
storage:
  - name: cache
    size: 4Gi
    attributes:
      class: ram
```

**Note:** RAM storage cannot be persistent.

**Characteristics:**
- Backed by system RAM
- Fastest possible I/O
- Data lost on restart
- Counts against memory quota

**Best for:**
- Application caches
- Session storage
- Temporary file processing
- Build artifacts

## Validation Rules

### RAM Cannot Be Persistent

```yaml
# INVALID - will fail validation
storage:
  - name: cache
    size: 4Gi
    attributes:
      class: ram
      persistent: true  # Error!
```

### Non-Default Classes Require Persistent Flag

```yaml
# INVALID - beta2/beta3 require persistent: true
storage:
  - name: data
    size: 10Gi
    attributes:
      class: beta2
      persistent: false  # Error!

# VALID
storage:
  - name: data
    size: 10Gi
    attributes:
      class: beta2
      persistent: true
```

## Size Specifications

Use standard Kubernetes size suffixes:

| Suffix | Meaning | Example |
|--------|---------|---------|
| `Ki` | Kibibytes (1024) | `512Ki` |
| `Mi` | Mebibytes (1024²) | `512Mi` |
| `Gi` | Gibibytes (1024³) | `100Gi` |
| `Ti` | Tebibytes (1024⁴) | `1Ti` |

## Storage Guidelines

### Database Storage

```yaml
# PostgreSQL with data and WAL separation
profiles:
  compute:
    postgres:
      resources:
        cpu:
          units: 2
        memory:
          size: 4Gi
        storage:
          - name: default
            size: 1Gi
          - name: pgdata
            size: 100Gi
            attributes:
              persistent: true
              class: beta2
          - name: pgwal
            size: 20Gi
            attributes:
              persistent: true
              class: beta3  # Fast NVMe for WAL
```

### Web Application with Uploads

```yaml
profiles:
  compute:
    webapp:
      resources:
        cpu:
          units: 1
        memory:
          size: 1Gi
        storage:
          - name: default
            size: 2Gi
          - name: uploads
            size: 50Gi
            attributes:
              persistent: true
              class: beta2
```

### Cache-Heavy Application

```yaml
profiles:
  compute:
    cache-app:
      resources:
        cpu:
          units: 2
        memory:
          size: 8Gi
        storage:
          - name: default
            size: 1Gi
          - name: cache
            size: 4Gi
            attributes:
              class: ram
```

## Provider Availability

Not all providers support all storage classes. Use provider attributes to filter:

```yaml
profiles:
  placement:
    dcloud:
      attributes:
        capabilities/storage/2/class: beta3  # Require beta3 support
      pricing:
        web:
          denom: uact
          amount: 2000
```

## Cost Considerations

Storage costs are included in the overall bid price. Higher-performance storage classes (beta3) may result in:
- Higher bid prices from providers
- Fewer available providers
- Better I/O performance

Balance performance needs against cost and availability.
