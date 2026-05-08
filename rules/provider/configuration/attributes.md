# Provider Attributes

Provider attributes are key-value pairs that describe a provider's capabilities, location, and features. Tenants use attributes to filter providers in their SDL placement configuration.

## How Attributes Work

```
┌─────────────┐         ┌──────────────┐         ┌──────────────┐
│  Provider   │ ──1──►  │  On-Chain    │ ◄──3──  │   Tenant     │
│  Registers  │         │  Attributes  │         │   SDL Filter │
│  Attributes │         │              │         │              │
└─────────────┘         └──────┬───────┘         └──────────────┘
                               │
                          2    │
                               ▼
                        ┌──────────────┐
                        │   Auditor    │
                        │   Signs      │
                        │   Attributes │
                        └──────────────┘
```

1. Provider registers attributes on-chain
2. Auditors verify and sign provider attributes
3. Tenants filter by attributes and auditor signatures in SDL

## Standard Attributes

### Core Attributes

| Key | Values | Description |
|-----|--------|-------------|
| `region` | `us-west`, `us-east`, `eu-west`, `eu-east`, `ap-southeast` | Geographic region |
| `host` | `akash` | Hosting platform identifier |
| `tier` | `community`, `professional`, `enterprise` | Provider tier level |
| `organization` | Organization name | Provider organization |
| `email` | Email address | Contact email |
| `website` | URL | Provider website |

### Capability Attributes

| Key | Values | Description |
|-----|--------|-------------|
| `capabilities/storage/1/class` | `beta2`, `beta3`, `ram` | Available storage classes |
| `capabilities/storage/1/persistent` | `true`, `false` | Persistent storage support |
| `capabilities/gpu/vendor/nvidia/model/<model>` | `true` | GPU model availability |
| `capabilities/ip/ip_lease` | `true` | Dedicated IP lease support |

### GPU Attributes

| Key | Description |
|-----|-------------|
| `capabilities/gpu/vendor/nvidia/model/a100` | NVIDIA A100 available |
| `capabilities/gpu/vendor/nvidia/model/a100/ram/80Gi` | A100 80GB variant |
| `capabilities/gpu/vendor/nvidia/model/a100/interface/sxm` | A100 SXM interface |
| `capabilities/gpu/vendor/nvidia/model/rtx3090` | RTX 3090 available |
| `capabilities/gpu/vendor/nvidia/model/t4` | T4 available |
| `capabilities/gpu/vendor/nvidia/model/h100` | H100 available |

## Configuring Attributes

### In Provider Registration

```yaml
# provider.yaml
host: https://provider.example.com:8443
attributes:
  - key: region
    value: us-west
  - key: host
    value: akash
  - key: tier
    value: community
  - key: organization
    value: myorg
  - key: capabilities/storage/1/class
    value: beta2
  - key: capabilities/storage/1/persistent
    value: "true"
  - key: capabilities/storage/2/class
    value: ram
  - key: capabilities/storage/2/persistent
    value: "false"
  - key: capabilities/gpu/vendor/nvidia/model/a100
    value: "true"
  - key: capabilities/gpu/vendor/nvidia/model/a100/ram/80Gi
    value: "true"
  - key: capabilities/gpu/vendor/nvidia/model/a100/interface/sxm
    value: "true"
info:
  email: provider@example.com
  website: https://example.com
```

### Register Attributes On-Chain

```bash
# Create provider with attributes
akash tx provider create provider.yaml \
  --from provider-wallet \
  --chain-id akashnet-2 \
  --node https://rpc.akashnet.net:443 \
  --gas-prices 0.025uakt \
  --gas auto \
  --gas-adjustment 1.5
```

### Update Attributes

```bash
# Update provider attributes
akash tx provider update provider.yaml \
  --from provider-wallet \
  --chain-id akashnet-2 \
  --node https://rpc.akashnet.net:443 \
  --gas-prices 0.025uakt \
  --gas auto \
  --gas-adjustment 1.5
```

### Query Provider Attributes

```bash
# View provider registration
akash query provider get <PROVIDER_ADDRESS> \
  --node https://rpc.akashnet.net:443

# List all providers
akash query provider list \
  --node https://rpc.akashnet.net:443
```

## Auditor Signatures

Auditors are trusted entities that verify provider claims. Tenants can require auditor signatures in their SDL to ensure provider attributes are verified.

### How Auditor Signing Works

1. Provider registers attributes on-chain
2. Auditor verifies provider capabilities (hardware, location, etc.)
3. Auditor signs the provider's attributes on-chain
4. Tenants reference auditor addresses in their SDL `signedBy` field

### Akash Network Auditors

| Auditor | Address | Description |
|---------|---------|-------------|
| Akash Network | `akash1365ez...` | Official Akash auditor |

### Requesting Auditor Verification

1. Register your provider with accurate attributes
2. Contact the auditor organization (e.g., via Akash Discord)
3. Provide proof of capabilities (hardware specs, location, etc.)
4. Auditor verifies and signs attributes on-chain

### Auditor Signs Provider Attributes

```bash
# Auditor command to sign provider attributes
akash tx audit attr create \
  <PROVIDER_ADDRESS> \
  region=us-west host=akash tier=community \
  --from auditor-wallet \
  --chain-id akashnet-2 \
  --node https://rpc.akashnet.net:443
```

### Query Auditor Signatures

```bash
# Check which auditors have signed a provider
akash query audit attr list \
  --provider <PROVIDER_ADDRESS> \
  --node https://rpc.akashnet.net:443
```

## SDL Attribute Matching

Tenants filter providers using attributes in their SDL:

### Basic Attribute Filtering

```yaml
profiles:
  placement:
    dcloud:
      attributes:
        region:
          - us-west
      pricing:
        web:
          denom: uact
          amount: 1000
```

### With Auditor Requirement

```yaml
profiles:
  placement:
    dcloud:
      attributes:
        region:
          - us-west
        host:
          - akash
      signedBy:
        anyOf:
          - akash1365ez...   # Akash Network auditor
      pricing:
        web:
          denom: uact
          amount: 1000
```

### GPU Attribute Matching

```yaml
profiles:
  placement:
    dcloud:
      attributes:
        region:
          - us-west
      signedBy:
        anyOf:
          - akash1365ez...
      pricing:
        ml:
          denom: uact
          amount: 50000
```

GPU model matching happens in the compute profile, not attributes:

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
                  ram: 80Gi
```

## Example Provider Configurations

### CPU-Only Provider

```yaml
# provider.yaml
host: https://provider.example.com:8443
attributes:
  - key: region
    value: us-east
  - key: host
    value: akash
  - key: tier
    value: community
  - key: capabilities/storage/1/class
    value: beta2
  - key: capabilities/storage/1/persistent
    value: "true"
info:
  email: admin@example.com
  website: https://example.com
```

### GPU Provider (Multi-Model)

```yaml
# provider.yaml
host: https://gpu-provider.example.com:8443
attributes:
  - key: region
    value: us-west
  - key: host
    value: akash
  - key: tier
    value: professional
  - key: capabilities/storage/1/class
    value: beta2
  - key: capabilities/storage/1/persistent
    value: "true"
  - key: capabilities/storage/2/class
    value: ram
  - key: capabilities/storage/2/persistent
    value: "false"
  - key: capabilities/gpu/vendor/nvidia/model/a100
    value: "true"
  - key: capabilities/gpu/vendor/nvidia/model/a100/ram/80Gi
    value: "true"
  - key: capabilities/gpu/vendor/nvidia/model/a100/interface/sxm
    value: "true"
  - key: capabilities/gpu/vendor/nvidia/model/rtx3090
    value: "true"
info:
  email: gpu@example.com
  website: https://gpu-provider.example.com
```

### Enterprise Provider with IP Leases

```yaml
# provider.yaml
host: https://enterprise.example.com:8443
attributes:
  - key: region
    value: eu-west
  - key: host
    value: akash
  - key: tier
    value: enterprise
  - key: organization
    value: enterprise-cloud-co
  - key: capabilities/storage/1/class
    value: beta2
  - key: capabilities/storage/1/persistent
    value: "true"
  - key: capabilities/storage/2/class
    value: beta3
  - key: capabilities/storage/2/persistent
    value: "true"
  - key: capabilities/ip/ip_lease
    value: "true"
info:
  email: ops@enterprise.example.com
  website: https://enterprise.example.com
```

## Best Practices

| Practice | Recommendation |
|----------|---------------|
| Accuracy | Only advertise capabilities you actually have |
| Completeness | Include all relevant attributes (region, storage, GPU) |
| Auditing | Get attributes signed by an auditor to increase trust |
| Updates | Update attributes promptly when capabilities change |
| GPU Specifics | Include RAM size and interface for GPU attributes |
| Storage Classes | List all available storage classes |

## Next Steps

- **@pricing.md** - Configure pricing strategy
- **@bid-engine.md** - Configure bid engine behavior
