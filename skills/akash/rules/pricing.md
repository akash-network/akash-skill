# Akash Network Pricing

Understanding payment options, pricing calculations, and cost optimization on Akash Network.

## Payment Denominations

Akash has **two tokens**. Don't conflate them:

| Token | Denom | What it's for |
|---|---|---|
| **AKT** | `uakt` | Chain token — gas (`--gas-prices`), staking, validator rewards. `1 AKT = 1,000,000 uakt`. |
| **ACT** | `uact` | Deployment-payment token — SDL pricing, bid *prices* (the rate providers offer), deployment escrow/deposit, lease payments. `1 ACT = 1,000,000 uact`. Note: the provider-side bid *deposit* (anti-spam collateral on `MsgCreateBid`) is uakt, not uact. |

**AKT and ACT are separate tokens.** Self-custody deployers must mint ACT by burning AKT before depositing to a deployment. Console API users skip this — Console funds the managed wallet with ACT directly (Stripe → USD → ACT server-side).

### uact (deployment-payment denom)

Used in SDL pricing, deployment deposits, and lease payments:

```yaml
pricing:
  web:
    denom: uact
    amount: 1000
```

`1 ACT = 1,000,000 uact`. Values in deployment messages (`MsgDepositDeployment`, escrow balances, bid amounts) are denominated in `uact`.

### USDC via IBC

Stable coin payment using IBC (Inter-Blockchain Communication):

```yaml
pricing:
  web:
    denom: ibc/170C677610AC31DF0904FFE09CD3B5C657492170E7E52372E48756B71E56F2F1
    amount: 100
```

The IBC denom hash represents USDC from the Noble chain bridged to Akash.

### USDC Denom Reference

```
ibc/170C677610AC31DF0904FFE09CD3B5C657492170E7E52372E48756B71E56F2F1
```

This is the official USDC denomination on Akash Network via IBC from Noble.

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

**Example with uact:**
```yaml
pricing:
  web:
    denom: uact
    amount: 1000

# Monthly cost: 1000 × 438,000 = 438,000,000 uact = 438 ACT
```

**Example with USDC:**
```yaml
pricing:
  web:
    denom: ibc/170C677610AC31DF0904FFE09CD3B5C657492170E7E52372E48756B71E56F2F1
    amount: 10

# Monthly cost: 10 × 438,000 = 4,380,000 uusdc = $4.38 USDC
```

## Pricing Guidelines

### By Workload Type

| Workload | CPU | Memory | Storage | uact/block | ~Monthly ACT |
|----------|-----|--------|---------|------------|--------------|
| Static Site | 0.25 | 256Mi | 512Mi | 300-500 | 130-220 |
| Web App | 0.5 | 512Mi | 1Gi | 500-1000 | 220-438 |
| API Server | 1-2 | 1-2Gi | 5Gi | 1000-2000 | 438-876 |
| Database | 2 | 2-4Gi | 20Gi+ | 2000-5000 | 876-2190 |
| ML Inference | 4 | 8Gi | 20Gi | 3000-5000 | 1314-2190 |

### GPU Pricing

| GPU Model | VRAM | uact/block | ~Monthly ACT |
|-----------|------|------------|--------------|
| T4 | 16GB | 10000-20000 | 4380-8760 |
| RTX 3080 | 10GB | 15000-25000 | 6570-10950 |
| RTX 3090 | 24GB | 18000-30000 | 7884-13140 |
| A10 | 24GB | 25000-40000 | 10950-17520 |
| RTX A6000 | 48GB | 35000-50000 | 15330-21900 |
| A100 40GB | 40GB | 40000-60000 | 17520-26280 |
| A100 80GB | 80GB | 60000-100000 | 26280-43800 |

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

For a 1000 uact/block deployment:
```
1000 × 14400 × 7 = 100,800,000 uact = 100.8 ACT
```

### Escrow Monitoring

Check escrow balance regularly:

```bash
akash query deployment get --owner <address> --dseq <dseq>
```

Add funds before depletion:

```bash
akash tx deployment deposit <amount>uact --owner <address> --dseq <dseq>
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

### Choose Payment Currency Wisely

- **uact** - The default. Required if you don't want to deal with bridged stablecoins. Console-API users get this with no extra steps.
- **USDC (IBC)** - Best for predictable USD-denominated costs. Self-custody only — bridge USDC from Noble to Akash first.

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
akash query market lease list --state active
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
