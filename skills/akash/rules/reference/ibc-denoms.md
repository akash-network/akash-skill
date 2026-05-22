# IBC Denominations Reference

Payment denominations available on Akash Network via Inter-Blockchain Communication (IBC).

## Native Token

### AKT (uact)

The native Akash token:

```yaml
pricing:
  web:
    denom: uact
    amount: 1000
```

**Conversion:**
```
1 AKT = 1,000,000 uact
```

## IBC Tokens

### USDC (from Noble)

The primary stablecoin for Akash payments:

```yaml
pricing:
  web:
    denom: ibc/170C677610AC31DF0904FFE09CD3B5C657492170E7E52372E48756B71E56F2F1
    amount: 100
```

**Full Denom:**
```
ibc/170C677610AC31DF0904FFE09CD3B5C657492170E7E52372E48756B71E56F2F1
```

**Origin:** Noble chain (native USDC issuer)

**Conversion:**
```
1 USDC = 1,000,000 uusdc
```

## Denom Reference Table

| Token | Denom | Decimals | Source |
|-------|-------|----------|--------|
| AKT | `uact` | 6 | Native |
| USDC | `ibc/170C677610AC31DF0904FFE09CD3B5C657492170E7E52372E48756B71E56F2F1` | 6 | Noble |

## Using IBC Tokens

### In SDL Pricing

```yaml
profiles:
  placement:
    dcloud:
      pricing:
        web:
          denom: ibc/170C677610AC31DF0904FFE09CD3B5C657492170E7E52372E48756B71E56F2F1
          amount: 50  # ~$0.00005 per block

        api:
          denom: ibc/170C677610AC31DF0904FFE09CD3B5C657492170E7E52372E48756B71E56F2F1
          amount: 100  # ~$0.0001 per block
```

### In CLI Commands

```bash
# Deposit USDC to deployment
akash tx deployment deposit \
  1000000ibc/170C677610AC31DF0904FFE09CD3B5C657492170E7E52372E48756B71E56F2F1 \
  --dseq <dseq>
```

## Obtaining IBC Tokens

### USDC on Akash

1. **Centralized Exchange** - Buy USDC on Noble-supported exchanges
2. **IBC Transfer** - Transfer from Noble to Akash
3. **DEX** - Swap on Osmosis or other Cosmos DEXs

### IBC Transfer Command

```bash
# From Noble to Akash (conceptual)
# Use a wallet like Keplr for easier transfers
```

## Price Calculations

### USDC Pricing

```yaml
pricing:
  web:
    denom: ibc/170C677610AC31DF0904FFE09CD3B5C657492170E7E52372E48756B71E56F2F1
    amount: 10  # 10 uusdc = $0.00001 per block
```

**Monthly cost calculation:**
```
blocks_per_month ≈ 438,000
monthly_cost = 10 × 438,000 = 4,380,000 uusdc = $4.38
```

### AKT vs USDC Comparison

| Metric | uact | USDC |
|--------|------|------|
| Price Stability | Volatile | Stable |
| Availability | High | Moderate |
| Provider Support | Universal | Most providers |
| Cost Predictability | Low | High |

## Choosing Payment Token

### Use AKT (uact) When:

- AKT price is low relative to compute value
- You hold AKT and want to use it
- Maximum provider compatibility needed
- Willing to accept price volatility

### Use USDC When:

- Predictable costs are important
- Budgeting in USD terms
- Hedging against AKT price movements
- Enterprise/business deployments

## Querying Balances

### Check Account Balances

```bash
akash query bank balances <your-address>
```

**Output:**
```yaml
balances:
- amount: "1000000000"
  denom: uact
- amount: "500000000"
  denom: ibc/170C677610AC31DF0904FFE09CD3B5C657492170E7E52372E48756B71E56F2F1
```

### Check Deployment Escrow

```bash
akash query deployment get --owner <address> --dseq <dseq>
```

## Mixed Currency Deployments

You can use different currencies for different placements:

```yaml
profiles:
  placement:
    primary:
      pricing:
        web:
          denom: uact
          amount: 1000

    backup:
      pricing:
        web:
          denom: ibc/170C677610AC31DF0904FFE09CD3B5C657492170E7E52372E48756B71E56F2F1
          amount: 50
```

**Note:** The escrow deposit must match the currency used in pricing.

## Future IBC Tokens

The Akash Network may support additional IBC tokens in the future. Check the official documentation for updates on supported denominations.

## Validation Rules

### Denom Format

```yaml
# VALID - Native AKT
denom: uact

# VALID - IBC token
denom: ibc/170C677610AC31DF0904FFE09CD3B5C657492170E7E52372E48756B71E56F2F1

# INVALID - Wrong format
denom: usdc        # Must use ibc/... format
denom: USD         # Not a valid denom
denom: akt         # Must be uact (micro-denomination)
```

### Amount Must Be Positive Integer

```yaml
# VALID
amount: 1000

# INVALID
amount: -100    # Negative
amount: 10.5    # Decimal
amount: "1000"  # String (may work but not recommended)
```
