# Compute Resources Configuration

The `profiles.compute` section defines resource requirements for each service profile.

## Basic Structure

```yaml
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
```

## CPU Configuration

CPU units can be specified in three formats:

| Format | Example | Description |
|--------|---------|-------------|
| Decimal | `0.5` | Half a CPU core |
| Integer | `2` | Two CPU cores |
| Millicores | `500m` | 500 millicores (= 0.5 cores) |

```yaml
profiles:
  compute:
    web:
      resources:
        cpu:
          units: 0.5      # Half a core

    api:
      resources:
        cpu:
          units: 2        # Two cores

    worker:
      resources:
        cpu:
          units: 1500m    # 1.5 cores
```

## Memory Configuration

Memory size with standard suffixes:

| Suffix | Meaning | Example |
|--------|---------|---------|
| `Ki` | Kibibytes (1024) | `512Ki` |
| `Mi` | Mebibytes (1024²) | `512Mi` |
| `Gi` | Gibibytes (1024³) | `2Gi` |
| `Ti` | Tebibytes (1024⁴) | `1Ti` |
| `k` | Kilobytes (1000) | `512k` |
| `M` | Megabytes (1000²) | `512M` |
| `G` | Gigabytes (1000³) | `2G` |
| `T` | Terabytes (1000⁴) | `1T` |

```yaml
profiles:
  compute:
    web:
      resources:
        memory:
          size: 512Mi     # 512 mebibytes

    ml:
      resources:
        memory:
          size: 16Gi      # 16 gibibytes
```

## Storage Configuration

### Simple Storage

Single ephemeral storage volume:

```yaml
profiles:
  compute:
    web:
      resources:
        storage:
          size: 1Gi
```

### Named Storage Volumes

Array of named volumes for more control:

```yaml
profiles:
  compute:
    db:
      resources:
        storage:
          - name: default
            size: 1Gi
          - name: data
            size: 10Gi
            attributes:
              persistent: true
              class: beta2
```

### Storage Attributes

| Attribute | Values | Description |
|-----------|--------|-------------|
| `persistent` | `true`/`false` | Data survives restarts |
| `class` | `beta2`, `beta3`, `ram` | Storage class type |

```yaml
storage:
  - name: data
    size: 10Gi
    attributes:
      persistent: true
      class: beta2          # SSD storage

  - name: cache
    size: 1Gi
    attributes:
      persistent: false
      class: ram            # RAM-based (fast, volatile)
```

### Storage Constraints

1. **RAM class cannot be persistent**: `class: ram` with `persistent: true` is invalid
2. **Non-RAM with attributes requires persistent**: If using `class: beta2` or `beta3`, must set `persistent: true`

## GPU Configuration

For GPU workloads:

```yaml
profiles:
  compute:
    ml:
      resources:
        cpu:
          units: 4
        memory:
          size: 16Gi
        storage:
          size: 50Gi
        gpu:
          units: 1
          attributes:
            vendor:
              nvidia:
```

### GPU Attributes

```yaml
gpu:
  units: 1
  attributes:
    vendor:
      nvidia:
        - model: a100       # Specific model
          ram: 80Gi         # GPU memory
          interface: sxm    # Interface type: pcie or sxm
```

### Available GPU Models

Common NVIDIA models:
- `a100` - NVIDIA A100
- `a10` - NVIDIA A10
- `a6000` - NVIDIA RTX A6000
- `rtx3080` - NVIDIA RTX 3080
- `rtx3090` - NVIDIA RTX 3090
- `t4` - NVIDIA T4
- `v100` - NVIDIA V100

### GPU Constraints

1. **GPU with units > 0 must have attributes with vendor**
2. **GPU with units = 0 cannot have attributes**

```yaml
# Valid: GPU with vendor
gpu:
  units: 1
  attributes:
    vendor:
      nvidia:

# Valid: No GPU
gpu:
  units: 0

# Invalid: GPU without vendor
gpu:
  units: 1          # Error: must have vendor attribute
```

## Complete Example

```yaml
profiles:
  compute:
    frontend:
      resources:
        cpu:
          units: 0.5
        memory:
          size: 512Mi
        storage:
          size: 1Gi

    backend:
      resources:
        cpu:
          units: 2
        memory:
          size: 2Gi
        storage:
          - name: default
            size: 2Gi
          - name: uploads
            size: 10Gi
            attributes:
              persistent: true
              class: beta2

    ml-worker:
      resources:
        cpu:
          units: 8
        memory:
          size: 32Gi
        storage:
          size: 100Gi
        gpu:
          units: 2
          attributes:
            vendor:
              nvidia:
                - model: a100
                  ram: 80Gi
```
