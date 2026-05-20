# Provider Pricing Configuration

Configuring how your Akash provider calculates bid prices for deployment orders.

## Pricing Model Overview

Akash providers use a **bid pricing script** to dynamically calculate prices for each deployment order. The script receives resource requirements as JSON input and outputs a price in uact per block.

```
┌────────────────┐     JSON      ┌──────────────────┐     Price     ┌──────────┐
│ Deployment     │ ────────────► │ Bid Pricing      │ ────────────► │ Bid      │
│ Order          │  (resources)  │ Script           │  (uact/block) │ Submitted│
│ (from chain)   │               │ (on provider)    │               │          │
└────────────────┘               └──────────────────┘               └──────────┘
```

## Pricing Script Input

The bid pricing script receives a JSON object on stdin with the following fields:

| Field | Type | Unit | Description |
|-------|------|------|-------------|
| `cpu` | number | millicpu | CPU requested (1000 = 1 core) |
| `memory` | number | bytes | Memory requested |
| `storage` | number | bytes | Ephemeral storage requested |
| `gpu` | number | count | Number of GPUs requested |
| `gpu_model` | string | model name | GPU model (e.g., `a100`, `rtx3090`) |
| `persistent_storage` | number | bytes | Persistent storage requested |
| `persistent_storage_class` | string | class name | Storage class (e.g., `beta2`) |
| `ip_lease` | number | count | Number of IP addresses requested |
| `endpoint_quantity` | number | count | Number of endpoints |

Example input:

```json
{
  "cpu": 2000,
  "memory": 4294967296,
  "storage": 10737418240,
  "gpu": 1,
  "gpu_model": "a100",
  "persistent_storage": 107374182400,
  "persistent_storage_class": "beta2",
  "ip_lease": 0,
  "endpoint_quantity": 1
}
```

## Pricing Script Output

The script must output a single number: the total price in uact per block.

```
15.5
```

## Cost Calculation Reference

### Converting to Monthly Cost

```
Monthly Cost (uact) = price_per_block * 438,000
Monthly Cost (AKT)  = price_per_block * 438,000 / 1,000,000
```

### Target Monthly Revenue per Resource

Use these as guidelines for setting competitive prices:

| Resource | Unit | Low Price/mo | Mid Price/mo | High Price/mo |
|----------|------|-------------|-------------|---------------|
| CPU | 1 core | $2-5 | $5-10 | $10-20 |
| Memory | 1 GB | $1-3 | $3-5 | $5-10 |
| Ephemeral Storage | 1 GB | $0.01-0.05 | $0.05-0.10 | $0.10-0.20 |
| Persistent Storage (beta2) | 1 GB | $0.05-0.10 | $0.10-0.20 | $0.20-0.50 |
| GPU (T4) | 1 GPU | $50-100 | $100-200 | $200-350 |
| GPU (RTX 3090) | 1 GPU | $80-150 | $150-300 | $300-500 |
| GPU (A100 40GB) | 1 GPU | $200-400 | $400-700 | $700-1200 |
| GPU (A100 80GB) | 1 GPU | $300-600 | $600-1000 | $1000-2000 |
| GPU (H100) | 1 GPU | $500-1000 | $1000-2000 | $2000-3500 |
| IP Lease | 1 IP | $3-5 | $5-8 | $8-15 |

### Price per Block Formulas

Converting monthly target to per-block price (in uact):

```
price_per_block = (monthly_usd_target / akt_price_usd) * 1000000 / 438000
```

Example: Target $10/month per CPU core, AKT at $3.50:

```
price_per_block = ($10 / $3.50) * 1000000 / 438000 = 6.52 uact/block per core
```

## Example Pricing Scripts

### Basic Pricing Script

Simple linear pricing based on resource quantities:

```bash
#!/bin/bash
data_in=$(jq .)

cpu=$(echo "$data_in" | jq -r '.cpu')
memory=$(echo "$data_in" | jq -r '.memory')
storage=$(echo "$data_in" | jq -r '.storage')
gpu=$(echo "$data_in" | jq -r '.gpu // 0')

# Prices in uact per block
# CPU: ~$5/month per core at AKT=$3.50
cpu_price=$(echo "scale=6; $cpu / 1000 * 3.3" | bc)

# Memory: ~$3/month per GB at AKT=$3.50
memory_price=$(echo "scale=6; $memory / 1073741824 * 2.0" | bc)

# Storage: ~$0.05/month per GB at AKT=$3.50
storage_price=$(echo "scale=6; $storage / 1073741824 * 0.03" | bc)

# GPU: ~$300/month per GPU at AKT=$3.50
gpu_price=$(echo "scale=6; $gpu * 195.0" | bc)

total=$(echo "scale=6; $cpu_price + $memory_price + $storage_price + $gpu_price" | bc)

# Enforce minimum price
min=1.0
if (( $(echo "$total < $min" | bc -l) )); then
  total=$min
fi

echo "$total"
```

### GPU-Aware Pricing Script

Different prices based on GPU model:

```bash
#!/bin/bash
data_in=$(jq .)

cpu=$(echo "$data_in" | jq -r '.cpu')
memory=$(echo "$data_in" | jq -r '.memory')
storage=$(echo "$data_in" | jq -r '.storage')
gpu=$(echo "$data_in" | jq -r '.gpu // 0')
gpu_model=$(echo "$data_in" | jq -r '.gpu_model // "unknown"')
persistent_storage=$(echo "$data_in" | jq -r '.persistent_storage // 0')
ip_lease=$(echo "$data_in" | jq -r '.ip_lease // 0')

# CPU pricing (uact/block per millicpu)
cpu_price=$(echo "scale=6; $cpu / 1000 * 3.3" | bc)

# Memory pricing (uact/block per byte)
memory_price=$(echo "scale=6; $memory / 1073741824 * 2.0" | bc)

# Ephemeral storage pricing (uact/block per byte)
storage_price=$(echo "scale=6; $storage / 1073741824 * 0.03" | bc)

# Persistent storage pricing (uact/block per byte)
persistent_price=$(echo "scale=6; $persistent_storage / 1073741824 * 0.15" | bc)

# GPU pricing by model (uact/block per GPU)
gpu_price=0
if [ "$gpu" -gt 0 ]; then
  case "$gpu_model" in
    "t4")
      gpu_unit_price=65     # ~$100/month
      ;;
    "rtx3060")
      gpu_unit_price=50     # ~$77/month
      ;;
    "rtx3080")
      gpu_unit_price=100    # ~$154/month
      ;;
    "rtx3090")
      gpu_unit_price=130    # ~$200/month
      ;;
    "rtx4090")
      gpu_unit_price=195    # ~$300/month
      ;;
    "a10")
      gpu_unit_price=160    # ~$246/month
      ;;
    "a6000")
      gpu_unit_price=230    # ~$354/month
      ;;
    "a100")
      gpu_unit_price=325    # ~$500/month
      ;;
    "h100")
      gpu_unit_price=650    # ~$1000/month
      ;;
    *)
      gpu_unit_price=130    # Default ~$200/month
      ;;
  esac
  gpu_price=$(echo "scale=6; $gpu * $gpu_unit_price" | bc)
fi

# IP lease pricing (uact/block per IP)
ip_price=$(echo "scale=6; $ip_lease * 3.3" | bc)

# Total price
total=$(echo "scale=6; $cpu_price + $memory_price + $storage_price + $persistent_price + $gpu_price + $ip_price" | bc)

# Minimum bid floor
min=1.0
if (( $(echo "$total < $min" | bc -l) )); then
  total=$min
fi

echo "$total"
```

### USDC-Denominated Pricing Script

Calculate prices targeting USD values:

```bash
#!/bin/bash
data_in=$(jq .)

cpu=$(echo "$data_in" | jq -r '.cpu')
memory=$(echo "$data_in" | jq -r '.memory')
storage=$(echo "$data_in" | jq -r '.storage')
gpu=$(echo "$data_in" | jq -r '.gpu // 0')
gpu_model=$(echo "$data_in" | jq -r '.gpu_model // "unknown"')

# Pricing in USD terms (per month)
# Then convert to uact per block using AKT price
# Update AKT_PRICE regularly or fetch dynamically
AKT_PRICE=3.50

# Monthly USD targets
cpu_monthly_usd=5.0      # per core
memory_monthly_usd=2.5   # per GB
storage_monthly_usd=0.05 # per GB
gpu_monthly_usd=300.0    # per GPU (default)

# Convert monthly USD to uact per block
# formula: (monthly_usd / akt_price) * 1000000 / 438000
usd_to_uact_block() {
  echo "scale=6; ($1 / $AKT_PRICE) * 1000000 / 438000" | bc
}

cpu_rate=$(usd_to_uact_block $cpu_monthly_usd)
memory_rate=$(usd_to_uact_block $memory_monthly_usd)
storage_rate=$(usd_to_uact_block $storage_monthly_usd)

cpu_price=$(echo "scale=6; $cpu / 1000 * $cpu_rate" | bc)
memory_price=$(echo "scale=6; $memory / 1073741824 * $memory_rate" | bc)
storage_price=$(echo "scale=6; $storage / 1073741824 * $storage_rate" | bc)

# GPU pricing
gpu_price=0
if [ "$gpu" -gt 0 ]; then
  case "$gpu_model" in
    "a100") gpu_monthly_usd=700 ;;
    "h100") gpu_monthly_usd=1500 ;;
    "rtx3090") gpu_monthly_usd=200 ;;
    *) gpu_monthly_usd=300 ;;
  esac
  gpu_rate=$(usd_to_uact_block $gpu_monthly_usd)
  gpu_price=$(echo "scale=6; $gpu * $gpu_rate" | bc)
fi

total=$(echo "scale=6; $cpu_price + $memory_price + $storage_price + $gpu_price" | bc)

# Minimum 1 uact/block
if (( $(echo "$total < 1" | bc -l) )); then
  total=1
fi

echo "$total"
```

## Configuring the Pricing Script

### In Helm Values

```yaml
# provider-values.yaml
bidpricescript: |
  #!/bin/bash
  # Paste your pricing script here
  data_in=$(jq .)
  # ... pricing logic ...
  echo "$total"
```

### Apply Configuration

```bash
helm upgrade akash-provider akash/provider \
  --namespace akash-services \
  --values provider-values.yaml
```

## Testing Your Pricing Script

### Local Testing

```bash
# Save script to a file
chmod +x pricing-script.sh

# Test with sample input
echo '{"cpu":2000,"memory":4294967296,"storage":10737418240,"gpu":0}' | ./pricing-script.sh
# Expected: A numeric price value

# Test with GPU
echo '{"cpu":8000,"memory":34359738368,"storage":107374182400,"gpu":1,"gpu_model":"a100"}' | ./pricing-script.sh
# Expected: Higher price including GPU component

# Test with persistent storage
echo '{"cpu":1000,"memory":2147483648,"storage":5368709120,"gpu":0,"persistent_storage":53687091200,"persistent_storage_class":"beta2"}' | ./pricing-script.sh
```

### Verify in Provider Logs

```bash
# Watch provider logs for bid calculations
kubectl logs -n akash-services -l app=akash-provider -f | grep -i "bid\|price"
```

## Pricing Strategy Tips

| Strategy | Description |
|----------|-------------|
| Competitive | Price below market average to attract more deployments |
| Premium | Price above market for higher-quality infrastructure |
| GPU-Focused | Lower CPU/memory prices, premium GPU prices |
| Volume | Lower unit prices to attract more total deployments |
| Dynamic | Update AKT_PRICE variable regularly based on market |

### Market Rate Discovery

```bash
# Query active leases to see current market prices
akash query market lease list --state active \
  --node https://rpc.akashnet.net:443 \
  --output json | jq '.leases[].lease.price'
```

## Next Steps

- **@bid-engine.md** - Configure bid engine behavior
- **../operations/monitoring.md** - Monitor pricing effectiveness
