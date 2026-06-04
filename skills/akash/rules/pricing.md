# Akash Network Pricing

Understanding payment options, pricing calculations, and cost optimization on Akash Network.

## Payment Denominations

Akash has **two tokens**. Don't conflate them:

| Token | Denom | What it's for |
|---|---|---|
| **AKT** | `uakt` | Chain token — gas (`--gas-prices`), staking, validator rewards. `1 AKT = 1,000,000 uakt`. |
| **ACT** | `uact` | Deployment-payment token — SDL pricing, bid *prices* (the rate providers offer), deployment escrow/deposit, lease payments. `1 ACT = 1,000,000 uact`. Note: the provider-side bid *deposit* (`MsgCreateBid.deposit`, anti-spam collateral) accepts either uakt or uact — the chain `bid_min_deposits` lists both, default minimum 500000 (0.5 AKT) of either denom. |

**AKT and ACT are separate tokens.** Self-custody deployers must mint ACT by burning AKT before depositing to a deployment. Console API users skip this — Console funds the managed wallet with ACT directly (Stripe → USD → ACT server-side).

### uact (deployment-payment denom)

Used in SDL pricing, deployment deposits, and lease payments:

```yaml
pricing:
  web:
    denom: uact
    amount: 1000
```

`1 ACT = 1,000,000 uact`. Values in deployment messages (`MsgDepositDeployment`, escrow balances, bid amounts) are denominated in `uact`. `uact` is the standard SDL pricing/deposit denom post-Mainnet-17; the chain still accepts `uakt` deposits as well (`min_deposits` lists both `uact` and `uakt`).

## Pricing Model

### Per-Block Billing

Akash charges per block (~6 seconds):

```
Blocks per minute: ~10
Blocks per hour: ~600
Blocks per day: ~14,400
Blocks per month: ~438,000
```

### Price Calculation

```
Monthly Cost = bid_amount × blocks_per_month
```

**Illustrative example with uact** (multiply the per-block `amount` by blocks-per-month to estimate cost — actual rates come from live bids, not this figure):
```yaml
pricing:
  web:
    denom: uact
    amount: 1000

# Monthly cost ≈ amount × blocks_per_month (uact). Convert to ACT by dividing by 1,000,000.
# Use live price discovery and real awesome-akash templates for realistic numbers.
```

## Pricing Guidelines

These are illustrative starting points only. Real market rates come from live bids — use price discovery (Akash Console or CLI) and current awesome-akash templates rather than treating these as quotes.

### By Workload Type

| Workload | CPU | Memory | Storage |
|----------|-----|--------|---------|
| Static Site | 0.25 | 256Mi | 512Mi |
| Web App | 0.5 | 512Mi | 1Gi |
| API Server | 1-2 | 1-2Gi | 5Gi |
| Database | 2 | 2-4Gi | 20Gi+ |
| ML Inference | 4 | 8Gi | 20Gi |

### GPU Pricing

GPU per-block rates vary widely by model, VRAM, and provider. Discover current rates from live bids rather than relying on fixed figures:

| GPU Model | VRAM |
|-----------|------|
| T4 | 16GB |
| RTX 3080 | 10GB |
| RTX 3090 | 24GB |
| RTX A6000 | 48GB |
| A100 40GB | 40GB |
| A100 80GB | 80GB |

## Escrow System

### How Escrow Works

1. **Deposit** - Funds locked when deployment created
2. **Drawdown** - Provider withdraws per block during lease
3. **Refund** - Remaining balance returned on close

### Minimum Escrow

Recommended escrow for deployment stability:

```
Minimum Escrow = bid_amount × blocks_per_day × 7
```

Multiply your per-block `amount` (in uact) by blocks-per-day and your desired runway in days; divide by 1,000,000 to express the result in ACT. Size this against your actual bid amount rather than a fixed figure.

### Escrow Monitoring

Check escrow balance regularly:

```bash
provider-services query deployment get --owner <address> --dseq <dseq>
```

Add funds before depletion:

```bash
provider-services tx deployment deposit <amount>uact --owner <address> --dseq <dseq>
```

## Cost Optimization

### Right-Size Resources

Start small and scale up:

```yaml
# Start with minimum viable resources
profiles:
  compute:
    web:
      resources:
        cpu:
          units: 0.25    # Quarter core
        memory:
          size: 256Mi    # Minimal memory
        storage:
          size: 512Mi    # Minimal storage
```

### Use Competitive Bidding

Set a maximum price and let providers compete:

```yaml
pricing:
  web:
    denom: uact
    amount: 2000  # Max you're willing to pay
```

Providers will bid at or below this amount.

### Payment Denomination

`uact` is the standard SDL pricing/deposit denom post-Mainnet-17; the chain still accepts `uakt` deposits as well (`min_deposits` lists both `uact` and `uakt`). Console-API users get `uact` funded automatically (Stripe → USD → ACT, server-side). Self-custody deployers mint ACT by burning AKT before depositing.

### Persistent vs Ephemeral Storage

Persistent storage costs more but survives restarts:

```yaml
# Ephemeral (cheaper, data lost on restart)
storage:
  size: 10Gi

# Persistent (more expensive, data survives)
storage:
  - name: data
    size: 10Gi
    attributes:
      persistent: true
      class: beta2
```

### Multi-Instance Deployment

Running multiple instances increases costs linearly:

```yaml
deployment:
  web:
    dcloud:
      profile: web
      count: 3  # 3x the cost of count: 1
```

## Comparing Costs

### Akash vs Traditional Cloud

| Service | AWS/GCP | Akash (est.) | Savings |
|---------|---------|--------------|---------|
| 1 vCPU, 2GB RAM | $30-50/mo | $5-15/mo | 70-85% |
| 4 vCPU, 16GB RAM | $120-200/mo | $20-50/mo | 70-85% |
| GPU (T4) | $300-500/mo | $50-150/mo | 70-80% |
| GPU (A100) | $2000-3000/mo | $300-700/mo | 70-85% |

*Actual prices vary based on provider bids and market conditions*

### Price Discovery

Use Akash Console or CLI to see current market rates:

```bash
# Query active leases for pricing data
provider-services query market lease list --state active
```

## IP Endpoint Costs

IP endpoints have additional costs:

```yaml
endpoints:
  public-ip:
    kind: ip
```

IP leases are billed separately from compute. Factor this into total deployment cost.

## Payment Flow

```
1. Tenant deposits escrow
   └── Funds locked in deployment account

2. Provider accepts bid
   └── Lease created at bid price

3. Per-block settlement
   └── Provider withdraws bid_amount each block

4. Deployment closed
   └── Remaining escrow returned to tenant
```

## Tax and Compliance

- Payments are on-chain and publicly visible
- Keep records of deployment transactions for tax purposes
- Consider the tax implications of AKT appreciation/depreciation
