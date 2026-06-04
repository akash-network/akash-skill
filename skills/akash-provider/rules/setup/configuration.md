# Initial Provider Configuration

Configuring the Akash provider after installation, including chain RPC, wallet, bid pricing, and withdrawal settings.

## Configuration Overview

Provider configuration is managed through:

1. **Helm chart values** - Primary configuration method
2. **Environment variables** - Override specific settings
3. **On-chain registration** - Provider attributes and host URI
4. **Bid pricing script** - Custom pricing logic

## Chain RPC Configuration

### Setting the RPC Endpoint

Configure the Akash blockchain RPC endpoint in Helm values:

```yaml
# provider-values.yaml
node: https://rpc.akashnet.net:443
chainid: akashnet-2
```

### Multiple RPC Endpoints

For redundancy, configure a primary and fallback:

```yaml
# Primary RPC
node: https://rpc.akashnet.net:443

# For high availability, run a local Akash node
# and point to it:
# node: http://akash-node:26657
```

### Running a Local RPC Node

For production providers, a dedicated Akash node is recommended:

```bash
# Install Akash node
akash init provider-node --chain-id akashnet-2

# Configure for RPC access
# Edit ~/.akash/config/config.toml
# Set laddr = "tcp://0.0.0.0:26657" in [rpc] section

# Start the node
akash start
```

### Recommended Public RPC Endpoints

| Endpoint | Provider |
|----------|----------|
| `https://rpc.akashnet.net:443` | Akash Network |
| `https://akash-rpc.polkachu.com:443` | Polkachu |
| `https://rpc-akash.ecostake.com:443` | Ecostake |
| `https://akash-rpc.lavenderfive.com:443` | Lavender Five |

## Wallet Configuration

### Key Management

The provider wallet key can be configured in several ways:

#### Option 1: Kubernetes Secret (Recommended)

```bash
# Create secret from keyring
kubectl create secret generic akash-provider-keys \
  --namespace akash-services \
  --from-file=key.pem=<KEY_FILE_PATH>
```

Reference in Helm values:

```yaml
keysecret: akash-provider-keys
from: provider-wallet
```

#### Option 2: Environment Variable

```yaml
# In Helm values or deployment env
env:
  - name: AKASH_FROM
    value: provider-wallet
  - name: AKASH_KEYRING_BACKEND
    value: test
```

### Wallet Balance Management

Ensure the provider wallet maintains sufficient AKT:

```bash
# Check balance
provider-services query bank balances $(provider-services keys show provider-wallet -a) \
  --node https://rpc.akashnet.net:443

# Send funds to provider wallet
provider-services tx bank send <SOURCE_WALLET> <PROVIDER_ADDRESS> 10000000uakt \
  --from <SOURCE_WALLET> \
  --chain-id akashnet-2 \
  --node https://rpc.akashnet.net:443
```

## Bid Pricing Script

The bid pricing script determines how much the provider charges for resources.

### Script Format

The script receives JSON input on stdin and outputs a price in uact per block:

```bash
#!/bin/bash
# Read resource request from stdin
data_in=$(jq .)

# Parse requested resources
cpu=$(echo "$data_in" | jq -r '.cpu')           # millicpu (1000 = 1 core)
memory=$(echo "$data_in" | jq -r '.memory')     # bytes
storage=$(echo "$data_in" | jq -r '.storage')   # bytes
gpu=$(echo "$data_in" | jq -r '.gpu')           # GPU count
gpu_model=$(echo "$data_in" | jq -r '.gpu_model // empty')

# Calculate price components (uact per block)
cpu_price=$(echo "scale=6; $cpu / 1000 * 1.5" | bc)
memory_price=$(echo "scale=6; $memory / 1073741824 * 0.8" | bc)
storage_price=$(echo "scale=6; $storage / 1073741824 * 0.02" | bc)

# GPU pricing by model
if [ "$gpu" -gt 0 ]; then
  case "$gpu_model" in
    "a100") gpu_unit_price=200 ;;
    "rtx3090") gpu_unit_price=80 ;;
    "t4") gpu_unit_price=40 ;;
    *) gpu_unit_price=100 ;;
  esac
  gpu_price=$(echo "scale=6; $gpu * $gpu_unit_price" | bc)
else
  gpu_price=0
fi

# Total price
total=$(echo "scale=6; $cpu_price + $memory_price + $storage_price + $gpu_price" | bc)

# Minimum bid floor
min_price=1
if (( $(echo "$total < $min_price" | bc -l) )); then
  total=$min_price
fi

echo "$total"
```

### Configure in Helm Values

```yaml
# provider-values.yaml
bidpricescript: |
  #!/bin/bash
  data_in=$(jq .)
  cpu=$(echo "$data_in" | jq -r '.cpu')
  memory=$(echo "$data_in" | jq -r '.memory')
  storage=$(echo "$data_in" | jq -r '.storage')
  gpu=$(echo "$data_in" | jq -r '.gpu')
  cpu_price=$(echo "scale=6; $cpu / 1000 * 1.5" | bc)
  memory_price=$(echo "scale=6; $memory / 1073741824 * 0.8" | bc)
  storage_price=$(echo "scale=6; $storage / 1073741824 * 0.02" | bc)
  gpu_price=$(echo "scale=6; $gpu * 100" | bc)
  total=$(echo "scale=6; $cpu_price + $memory_price + $storage_price + $gpu_price" | bc)
  echo "$total"
```

## Withdrawal Period

The withdrawal period controls how often the provider automatically withdraws earned funds from leases.

### Configuration

```yaml
# provider-values.yaml
# Period in blocks (~6 seconds per block)
withdrawalperiod: 720  # ~72 minutes (720 * 6s)
```

### Common Withdrawal Periods

| Blocks | Approximate Time | Use Case |
|--------|-----------------|----------|
| 60 | ~6 minutes | Frequent withdrawals, testing |
| 720 | ~72 minutes | Standard operation |
| 1440 | ~2.4 hours | Reduced transaction costs |
| 14400 | ~24 hours | Minimal transaction fees |

### Considerations

- Lower values = more frequent withdrawals but higher transaction costs
- Higher values = less frequent withdrawals but funds remain in escrow longer
- Each withdrawal is a blockchain transaction that costs gas

## Provider Configuration File Reference

Complete `provider-values.yaml` template:

```yaml
# ---- Chain Configuration ----
chainid: akashnet-2
node: https://rpc.akashnet.net:443

# ---- Provider Identity ----
from: provider-wallet
keysecret: akash-provider-keys
providerAddress: akash1...

# ---- Networking ----
domain: ingress.example.com
clusterPublicHostname: provider.example.com

# ---- Bid Settings ----
withdrawalperiod: 720
bidpricescript: |
  #!/bin/bash
  # ... pricing logic ...

# ---- Image Configuration ----
image:
  repository: ghcr.io/akash-network/provider
  tag: 0.12.0

# ---- Resource Limits ----
resources:
  limits:
    cpu: 2
    memory: 2Gi
  requests:
    cpu: 500m
    memory: 512Mi

# ---- Cluster Settings ----
cluster:
  # Maximum number of concurrent deployments
  maxDeployments: 100

  # Memory overcommit factor (1.0 = no overcommit)
  memoryOvercommitPercent: 0

  # CPU overcommit factor
  cpuOvercommitPercent: 0

# ---- Logging ----
log:
  level: info  # debug, info, warn, error

# ---- Feature Flags ----
features:
  # Enable IP lease support
  ipOperator: false

  # Enable persistent storage
  persistentStorage: true
```

## Environment Variable Overrides

Override Helm values with environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `AKASH_NODE` | RPC endpoint | From Helm values |
| `AKASH_CHAIN_ID` | Chain ID | `akashnet-2` |
| `AKASH_FROM` | Wallet key name | From Helm values |
| `AKASH_KEYRING_BACKEND` | Key storage backend | `os` |
| `AKASH_HOME` | Akash config directory | `~/.akash` |
| `AKASH_LOG_LEVEL` | Log verbosity | `info` |
| `AKASH_PROVIDER_DOMAIN` | Ingress domain | From Helm values |

### Setting Environment Variables in Helm

```yaml
# provider-values.yaml
env:
  - name: AKASH_LOG_LEVEL
    value: debug
  - name: AKASH_GAS_PRICES
    value: "0.025uakt"
  - name: AKASH_GAS_ADJUSTMENT
    value: "1.5"
```

## Applying Configuration Changes

```bash
# Update provider with new configuration
helm upgrade akash-provider akash/provider \
  --namespace akash-services \
  --values provider-values.yaml

# Verify the update
kubectl get pods -n akash-services -l app=akash-provider

# Watch provider logs after update
kubectl logs -n akash-services -l app=akash-provider -f
```

## Next Steps

- **../configuration/attributes.md** - Configure provider attributes
- **../configuration/pricing.md** - Detailed pricing configuration
- **../configuration/bid-engine.md** - Bid engine settings
