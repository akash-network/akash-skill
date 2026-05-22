# Provider Installation

Installing the Akash provider software on a Kubernetes cluster using Helm charts.

## Prerequisites

Before installing the provider:

- Kubernetes cluster running (1.27+)
- kubectl configured and working
- Helm 3.12+ installed
- Ingress controller deployed
- Provider wallet with AKT balance
- DNS records configured

## Step 1: Install Helm

```bash
# Install Helm (if not already installed)
curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Verify
helm version
```

## Step 2: Add Akash Helm Repository

```bash
# Add the Akash Helm repo
helm repo add akash https://akash-network.github.io/helm-charts
helm repo update
```

### Available Charts

| Chart | Description |
|-------|-------------|
| `akash/provider` | Core provider software |
| `akash/hostname-operator` | Manages ingress hostnames for tenants |
| `akash/inventory-operator` | Reports cluster resource availability |
| `akash/ip-operator` | Manages dedicated IP assignments (optional) |

## Step 3: Create Provider Namespace

```bash
kubectl create namespace akash-services
kubectl label namespace akash-services akash.network/name=akash-services akash.network=true
```

## Step 4: Configure Provider Wallet

### Import Wallet Key

```bash
# Create a Kubernetes secret with the provider wallet key
# Option 1: From existing key file
kubectl create secret generic akash-provider-keys \
  --namespace akash-services \
  --from-file=key.json=<PATH_TO_KEY_FILE>

# Option 2: From mnemonic (create key first, then import)
akash keys add provider-wallet --recover
# Enter mnemonic when prompted

# Export and create secret
akash keys export provider-wallet --unarmored-hex --unsafe 2>/dev/null | \
  kubectl create secret generic akash-provider-keys \
  --namespace akash-services \
  --from-literal=key-password="" \
  --from-file=key.pem=/dev/stdin
```

### Create Provider Certificate

```bash
# Generate provider certificate
akash tx cert create server provider.example.com \
  --from provider-wallet \
  --chain-id akashnet-2 \
  --node https://rpc.akashnet.net:443

# Verify certificate
akash query cert list --owner $(akash keys show provider-wallet -a) \
  --node https://rpc.akashnet.net:443
```

## Step 5: Provider Helm Values

Create `provider-values.yaml`:

```yaml
# provider-values.yaml
image:
  tag: 0.6.4  # Use latest stable version

# Chain configuration
chainid: akashnet-2
node: https://rpc.akashnet.net:443

# Provider identity
from: provider-wallet
key: <BASE64_ENCODED_KEY>
keysecret: akash-provider-keys

# Provider domain
domain: ingress.example.com

# Provider API
providerAddress: <PROVIDER_AKASH_ADDRESS>

# Withdrawal period (blocks between automatic withdrawals)
withdrawalperiod: 720  # ~72 minutes

# Bid pricing
bidpricescript: |
  #!/bin/bash
  # Pricing script - see configuration/pricing.md for details
  data_in=$(jq .)
  cpu=$(echo "$data_in" | jq -r '.cpu')
  memory=$(echo "$data_in" | jq -r '.memory')
  storage=$(echo "$data_in" | jq -r '.storage')
  gpu=$(echo "$data_in" | jq -r '.gpu')

  # Calculate price in uact per block
  cpu_price=$(echo "scale=6; $cpu * 1.5" | bc)
  memory_price=$(echo "scale=6; $memory / 1073741824 * 0.8" | bc)
  storage_price=$(echo "scale=6; $storage / 1073741824 * 0.02" | bc)
  gpu_price=$(echo "scale=6; $gpu * 100" | bc)

  total=$(echo "scale=6; $cpu_price + $memory_price + $storage_price + $gpu_price" | bc)
  echo "$total"

# Resource limits for the provider pod
resources:
  limits:
    cpu: 2
    memory: 2Gi
  requests:
    cpu: 500m
    memory: 512Mi

# Cluster public hostname
clusterPublicHostname: provider.example.com
```

### Key Configuration Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `chainid` | Akash chain ID | `akashnet-2` |
| `node` | RPC endpoint URL | `https://rpc.akashnet.net:443` |
| `from` | Wallet key name | `provider-wallet` |
| `domain` | Wildcard domain for tenant ingress | `ingress.example.com` |
| `withdrawalperiod` | Blocks between earnings withdrawal | `720` |
| `bidpricescript` | Script for calculating bid prices | See pricing configuration |
| `clusterPublicHostname` | Provider API hostname | `provider.example.com` |

## Step 6: Install Provider Chart

```bash
helm install akash-provider akash/provider \
  --namespace akash-services \
  --values provider-values.yaml
```

### Verify Provider Installation

```bash
# Check provider pod status
kubectl get pods -n akash-services -l app=akash-provider

# Check provider logs
kubectl logs -n akash-services -l app=akash-provider -f

# Expected log output when running correctly:
# "provider is running"
# "listening for on-chain events"
```

## Step 7: Install Hostname Operator

The hostname operator manages ingress routing for tenant deployments.

```bash
helm install hostname-operator akash/hostname-operator \
  --namespace akash-services \
  --set image.tag=0.6.4
```

### Verify Hostname Operator

```bash
kubectl get pods -n akash-services -l app=hostname-operator
kubectl logs -n akash-services -l app=hostname-operator
```

## Step 8: Install Inventory Operator

The inventory operator monitors and reports cluster resource availability.

```bash
helm install inventory-operator akash/inventory-operator \
  --namespace akash-services \
  --set image.tag=0.6.4
```

### Verify Inventory Operator

```bash
kubectl get pods -n akash-services -l app=inventory-operator
kubectl logs -n akash-services -l app=inventory-operator
```

## Step 9: Install IP Operator (Optional)

Required only if offering dedicated IP leases:

```bash
helm install ip-operator akash/ip-operator \
  --namespace akash-services \
  --set image.tag=0.6.4 \
  --set provider_address=<PROVIDER_AKASH_ADDRESS>
```

## Step 10: Register Provider On-Chain

Create `provider.yaml`:

```yaml
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
info:
  email: provider@example.com
  website: https://example.com
```

Register the provider:

```bash
akash tx provider create provider.yaml \
  --from provider-wallet \
  --chain-id akashnet-2 \
  --node https://rpc.akashnet.net:443 \
  --gas-prices 0.025uakt \
  --gas auto \
  --gas-adjustment 1.5
```

### Update Provider Registration

```bash
akash tx provider update provider.yaml \
  --from provider-wallet \
  --chain-id akashnet-2 \
  --node https://rpc.akashnet.net:443
```

## Upgrading the Provider

### Check Current Version

```bash
helm list -n akash-services
```

### Upgrade Charts

```bash
# Update Helm repos
helm repo update

# Upgrade provider
helm upgrade akash-provider akash/provider \
  --namespace akash-services \
  --values provider-values.yaml

# Upgrade hostname operator
helm upgrade hostname-operator akash/hostname-operator \
  --namespace akash-services

# Upgrade inventory operator
helm upgrade inventory-operator akash/inventory-operator \
  --namespace akash-services
```

## Uninstalling the Provider

```bash
# Remove provider components
helm uninstall akash-provider -n akash-services
helm uninstall hostname-operator -n akash-services
helm uninstall inventory-operator -n akash-services

# Remove namespace (optional)
kubectl delete namespace akash-services
```

## Installation Verification Checklist

```bash
# 1. All provider pods running
kubectl get pods -n akash-services
# Expected: provider, hostname-operator, inventory-operator all Running

# 2. Provider API accessible
curl -sk https://provider.example.com:8443/status

# 3. Provider registered on chain
akash query provider get <PROVIDER_ADDRESS> \
  --node https://rpc.akashnet.net:443

# 4. Provider certificate valid
akash query cert list --owner <PROVIDER_ADDRESS> \
  --node https://rpc.akashnet.net:443

# 5. Provider accepting bids (check logs)
kubectl logs -n akash-services -l app=akash-provider --tail=50
```

## Next Steps

- **@configuration.md** - Configure provider settings
- **../configuration/attributes.md** - Set up provider attributes
- **../configuration/pricing.md** - Configure pricing strategy
