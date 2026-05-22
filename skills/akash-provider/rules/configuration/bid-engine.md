# Bid Engine Configuration

The bid engine is the provider component that monitors the Akash blockchain for deployment orders, evaluates whether the provider can fulfill them, and automatically submits bids.

## How the Bid Engine Works

```
┌──────────────────────────────────────────────────────────────┐
│                       Bid Engine                             │
│                                                              │
│  1. Monitor    2. Filter      3. Check       4. Calculate    │
│  ┌────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   │
│  │ Watch  │──►│ Match    │──►│ Inventory│──►│ Pricing  │   │
│  │ Orders │   │ Attributes│  │ Available│   │ Script   │   │
│  └────────┘   └──────────┘   └──────────┘   └──────────┘   │
│                                                     │        │
│                                              5. Submit       │
│                                              ┌──────────┐   │
│                                              │ Bid to   │   │
│                                              │ Chain    │   │
│                                              └──────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### Bid Process Flow

1. **Monitor Orders** - The bid engine watches the blockchain for new deployment orders
2. **Filter by Attributes** - Orders are checked against provider attributes (region, tier, etc.)
3. **Check Inventory** - The inventory operator verifies sufficient resources are available
4. **Calculate Price** - The bid pricing script computes the bid amount
5. **Submit Bid** - If all checks pass, a bid transaction is broadcast to the chain

## Bid Engine Configuration

### Helm Values

```yaml
# provider-values.yaml

# ---- Bid Engine Settings ----

# Maximum number of concurrent bids
bidMaxConcurrent: 10

# Time to wait before bidding (gives other providers time to bid)
bidWaitDuration: 5s

# How long to wait for a bid to be accepted before timing out
bidTimeout: 5m

# Minimum deposit required in the order's escrow
bidMinDeposit: 5000000  # 5 ACT in uact (1 ACT = 1,000,000 uact)

# Filter orders by maximum resource request
bidMaxCPU: 256000       # 256 cores in millicpu
bidMaxMemory: 549755813888  # 512 GB in bytes
bidMaxStorage: 1099511627776  # 1 TB in bytes
bidMaxGPU: 8

# Bid pricing script (determines price)
bidpricescript: |
  #!/bin/bash
  # ... pricing logic ...
```

### Key Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `bidMaxConcurrent` | int | 10 | Maximum simultaneous bids |
| `bidWaitDuration` | duration | 5s | Delay before submitting bid |
| `bidTimeout` | duration | 5m | Bid acceptance timeout |
| `bidMinDeposit` | int | 5000000 | Minimum escrow deposit (uact) |
| `bidMaxCPU` | int | - | Max CPU per order (millicpu) |
| `bidMaxMemory` | int | - | Max memory per order (bytes) |
| `bidMaxStorage` | int | - | Max storage per order (bytes) |
| `bidMaxGPU` | int | - | Max GPUs per order |
| `bidpricescript` | string | - | Pricing script content |

## Order Filtering

### Attribute-Based Filtering

The bid engine only bids on orders whose SDL attributes match the provider's registered attributes.

**Order matches when:**

| Criteria | Condition |
|----------|-----------|
| Region | Order's region attribute matches provider's region |
| Host | Order's host attribute matches provider's host |
| Auditor | Provider is signed by the required auditor |
| GPU Model | Provider has the requested GPU model |
| Storage Class | Provider supports the requested storage class |
| IP Lease | Provider supports IP leases (if requested) |

**Order is skipped when:**

| Criteria | Condition |
|----------|-----------|
| Missing Attributes | Order requires attributes the provider does not have |
| Missing Auditor | Order requires auditor signature the provider lacks |
| Resource Exceeded | Requested resources exceed bid max limits |
| Insufficient Capacity | Not enough available resources in the cluster |

### Resource-Based Filtering

Configure maximum resource limits to prevent the provider from bidding on orders it cannot fulfill:

```yaml
# Prevent bidding on very large orders
bidMaxCPU: 128000           # 128 cores max per order
bidMaxMemory: 274877906944  # 256 GB max per order
bidMaxStorage: 549755813888 # 512 GB max per order
bidMaxGPU: 4                # 4 GPUs max per order
```

### Deposit Filtering

Reject orders with insufficient escrow deposits:

```yaml
# Require at least 5 AKT deposit
bidMinDeposit: 5000000  # uact
```

This protects against orders that would run out of funds quickly.

## Pricing Strategies

### Strategy 1: Fixed Markup

Constant price regardless of demand:

```bash
#!/bin/bash
data_in=$(jq .)
cpu=$(echo "$data_in" | jq -r '.cpu')
memory=$(echo "$data_in" | jq -r '.memory')
storage=$(echo "$data_in" | jq -r '.storage')
gpu=$(echo "$data_in" | jq -r '.gpu // 0')

# Fixed rates per unit
cpu_price=$(echo "scale=6; $cpu / 1000 * 3.0" | bc)
memory_price=$(echo "scale=6; $memory / 1073741824 * 1.5" | bc)
storage_price=$(echo "scale=6; $storage / 1073741824 * 0.03" | bc)
gpu_price=$(echo "scale=6; $gpu * 200" | bc)

total=$(echo "scale=6; $cpu_price + $memory_price + $storage_price + $gpu_price" | bc)
echo "$total"
```

### Strategy 2: Utilization-Based

Adjust prices based on current cluster utilization:

```bash
#!/bin/bash
data_in=$(jq .)
cpu=$(echo "$data_in" | jq -r '.cpu')
memory=$(echo "$data_in" | jq -r '.memory')
storage=$(echo "$data_in" | jq -r '.storage')
gpu=$(echo "$data_in" | jq -r '.gpu // 0')

# Get current utilization (simplified - in practice, query cluster metrics)
# Higher utilization = higher prices
UTILIZATION_FACTOR=1.0  # 1.0 = normal, 1.5 = 50% markup at high utilization

cpu_price=$(echo "scale=6; $cpu / 1000 * 3.0 * $UTILIZATION_FACTOR" | bc)
memory_price=$(echo "scale=6; $memory / 1073741824 * 1.5 * $UTILIZATION_FACTOR" | bc)
storage_price=$(echo "scale=6; $storage / 1073741824 * 0.03 * $UTILIZATION_FACTOR" | bc)
gpu_price=$(echo "scale=6; $gpu * 200 * $UTILIZATION_FACTOR" | bc)

total=$(echo "scale=6; $cpu_price + $memory_price + $storage_price + $gpu_price" | bc)
echo "$total"
```

### Strategy 3: Tenant Maximum Price

Bid just below the tenant's maximum price to maximize revenue:

```bash
#!/bin/bash
data_in=$(jq .)
max_price=$(echo "$data_in" | jq -r '.max_price // 0')

# If tenant's max price is available, bid slightly below
if [ "$max_price" != "0" ] && [ "$max_price" != "null" ]; then
  # Bid at 95% of max price
  total=$(echo "scale=6; $max_price * 0.95" | bc)
else
  # Fall back to standard pricing
  cpu=$(echo "$data_in" | jq -r '.cpu')
  memory=$(echo "$data_in" | jq -r '.memory')
  storage=$(echo "$data_in" | jq -r '.storage')
  gpu=$(echo "$data_in" | jq -r '.gpu // 0')

  cpu_price=$(echo "scale=6; $cpu / 1000 * 3.0" | bc)
  memory_price=$(echo "scale=6; $memory / 1073741824 * 1.5" | bc)
  storage_price=$(echo "scale=6; $storage / 1073741824 * 0.03" | bc)
  gpu_price=$(echo "scale=6; $gpu * 200" | bc)

  total=$(echo "scale=6; $cpu_price + $memory_price + $storage_price + $gpu_price" | bc)
fi

echo "$total"
```

## Bid Timing

### Wait Duration

The `bidWaitDuration` controls how long the provider waits before submitting a bid:

```yaml
# Wait 5 seconds before bidding (default)
bidWaitDuration: 5s

# Bid immediately (more competitive, higher gas costs)
bidWaitDuration: 0s

# Wait longer (less competitive, lower gas costs)
bidWaitDuration: 15s
```

### Bid Timeout

How long to keep a bid open before cancelling:

```yaml
# Default: 5 minutes
bidTimeout: 5m

# Shorter timeout for busy providers
bidTimeout: 2m
```

## Concurrency Control

### Maximum Concurrent Bids

Limit the number of simultaneous outstanding bids:

```yaml
# Allow up to 20 concurrent bids
bidMaxConcurrent: 20
```

**Considerations:**

| Setting | Effect |
|---------|--------|
| Low (1-5) | Conservative, fewer gas costs, may miss orders |
| Medium (10-20) | Balanced approach for most providers |
| High (20-50) | Aggressive, captures more orders, higher gas costs |

## Monitoring Bid Activity

### Check Bid Status via CLI

```bash
# List provider's active bids
akash query market bid list \
  --provider <PROVIDER_ADDRESS> \
  --state open \
  --node https://rpc.akashnet.net:443

# List provider's won leases
akash query market lease list \
  --provider <PROVIDER_ADDRESS> \
  --state active \
  --node https://rpc.akashnet.net:443
```

### Provider Logs

```bash
# Watch bid engine activity
kubectl logs -n akash-services -l app=akash-provider -f | grep -i "bid"

# Common log messages
# "submitting bid" - bid being submitted
# "bid accepted" - tenant accepted the bid
# "bid closed" - bid expired or was outbid
# "skipping order" - order does not match provider
```

### Bid Success Metrics

Track these metrics to optimize bidding:

| Metric | Description | Target |
|--------|-------------|--------|
| Bid Win Rate | % of bids accepted by tenants | 20-40% |
| Time to Bid | Seconds from order to bid submission | < 10s |
| Active Leases | Number of running deployments | Provider capacity |
| Revenue per Block | Total uact earned per block | Business goal |

## Troubleshooting Bids

### No Bids Being Submitted

```bash
# Check provider is running
kubectl get pods -n akash-services -l app=akash-provider

# Check provider logs for errors
kubectl logs -n akash-services -l app=akash-provider --tail=100

# Verify provider is registered on chain
akash query provider get <PROVIDER_ADDRESS> --node https://rpc.akashnet.net:443

# Check wallet balance (need gas for bids)
akash query bank balances <PROVIDER_ADDRESS> --node https://rpc.akashnet.net:443
```

### Bids Submitted but Never Accepted

- Check if pricing is competitive (may be too high)
- Verify attributes match common SDL requirements
- Ensure auditor signatures are current
- Check provider uptime and reliability

### Pricing Script Errors

```bash
# Test pricing script manually
echo '{"cpu":1000,"memory":1073741824,"storage":5368709120,"gpu":0}' | \
  kubectl exec -n akash-services -i deployment/akash-provider -- /bin/bash -c 'cat | /pricing-script.sh'
```

## Next Steps

- **../operations/monitoring.md** - Monitor provider performance
- **../operations/lease-management.md** - Manage active leases
