# Placement and Pricing Configuration

The `profiles.placement` section defines where deployments run and their pricing.

## Basic Structure

```yaml
profiles:
  placement:
    <placement-name>:
      pricing:
        <profile-name>:
          denom: uact
          amount: 1000
```

## Placement Properties

### pricing (required)

Defines the maximum price you're willing to pay per block for each compute profile:

```yaml
profiles:
  placement:
    dcloud:
      pricing:
        web:
          denom: uact
          amount: 1000
        api:
          denom: uact
          amount: 2000
```

### attributes (optional)

Filter providers by attributes:

```yaml
profiles:
  placement:
    dcloud:
      attributes:
        region: us-west
        host: akash
      pricing:
        web:
          denom: uact
          amount: 1000
```

Common attributes:
- `region` - Geographic region
- `host` - Hosting provider name
- `tier` - Service tier level

### signedBy (optional)

Require providers to be audited:

```yaml
profiles:
  placement:
    dcloud:
      signedBy:
        anyOf:
          - akash1365yvmc4s7awdyj3n2sav7xfx76adc6dnmlx63
          - akash18qa2a2ltfyvkyj0ggj3hkvuj6twzyumuaru9s4
      pricing:
        web:
          denom: uact
          amount: 1000
```

#### signedBy Options

| Field | Description |
|-------|-------------|
| `anyOf` | Provider signed by at least one of these auditors |
| `allOf` | Provider must be signed by all of these auditors |

```yaml
signedBy:
  allOf:
    - akash1auditor1...
    - akash1auditor2...
  anyOf:
    - akash1auditor3...
```

## Payment Denominations

### uact (ACT — the deployment-payment token)

ACT is Akash's deployment-payment token (distinct from AKT, the chain token used for gas/staking). `uact` is its micro-denomination — `1 ACT = 1,000,000 uact`. `uact` is the standard SDL pricing/deposit denom post-Mainnet-17; the chain still accepts `uakt` deposits as well (`min_deposits` lists both `uact` and `uakt`).

```yaml
pricing:
  web:
    denom: uact
    amount: 1000      # 0.001 ACT per block
```

### Price Calculation

- Prices are set per block, and blocks are produced at a roughly fixed cadence, so the `amount` you set translates into an ongoing per-block spend that accumulates over the lease.
- The block-based `amount` is a bid ceiling, not the final cost — the actual lease price is whatever a provider bids at or below it.
- Any monthly estimate derived from the per-block `amount` is illustrative only — rely on live price discovery (the bids you actually receive) and compare against real pricing in the [awesome-akash](https://github.com/akash-network/awesome-akash) example templates rather than a fixed multiplier.

## Multiple Placements

You can define multiple placement options:

```yaml
profiles:
  placement:
    us-east:
      attributes:
        region: us-east
      signedBy:
        anyOf:
          - akash1auditor...
      pricing:
        web:
          denom: uact
          amount: 1000

    eu-west:
      attributes:
        region: eu-west
      pricing:
        web:
          denom: uact
          amount: 1200
```

## Complete Example

```yaml
profiles:
  compute:
    web:
      resources:
        cpu:
          units: 1
        memory:
          size: 1Gi
        storage:
          size: 5Gi

    api:
      resources:
        cpu:
          units: 2
        memory:
          size: 2Gi
        storage:
          size: 10Gi

  placement:
    primary:
      attributes:
        region: us-west
      signedBy:
        anyOf:
          - akash1365yvmc4s7awdyj3n2sav7xfx76adc6dnmlx63
      pricing:
        web:
          denom: uact
          amount: 1000
        api:
          denom: uact
          amount: 2000

    backup:
      attributes:
        region: eu-central
      pricing:
        web:
          denom: uact
          amount: 1200
        api:
          denom: uact
          amount: 2200
```

## Pricing Guidelines

The ranges below are rough, illustrative starting points for the per-block `amount` (in `uact`) — not exact prices. Treat them as a place to begin, then let live bids and current market conditions guide the real value.

| Workload Type | Illustrative uact/block | Notes |
|---------------|---------------------|-------|
| Small web app | 500-1000 | 0.5 CPU, 512Mi RAM |
| API server | 1000-2000 | 1-2 CPU, 1-2Gi RAM |
| Database | 2000-5000 | Depends on storage |
| GPU workload | 10000-50000+ | Varies by GPU model |

Higher pricing increases the likelihood of provider acceptance. Start within these illustrative ranges and adjust based on the bids you receive and current market conditions.
