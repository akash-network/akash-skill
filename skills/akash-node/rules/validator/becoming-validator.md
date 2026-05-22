# Becoming a Validator

## Prerequisites

Before creating a validator, you must have:

| Requirement | Description |
|-------------|-------------|
| Running full node | A fully synced Akash full node (`catching_up: false`) |
| AKT tokens | Sufficient AKT for self-delegation and transaction fees |
| Wallet | An Akash wallet with funds (created via `akash keys add`) |
| Backup | Secure backup of your validator key and mnemonic |

### Verify Node is Synced

```bash
# Check sync status - "catching_up" must be false
akash status 2>&1 | jq '.SyncInfo.catching_up'
# Expected output: false
```

### Create or Import a Wallet

```bash
# Create a new wallet
akash keys add validator-wallet

# IMPORTANT: Save the mnemonic phrase securely!
# The mnemonic is displayed only once during key creation.

# Or import an existing wallet from mnemonic
akash keys add validator-wallet --recover

# Or import from a keyfile
akash keys import validator-wallet keyfile.json

# Check wallet balance
akash query bank balances $(akash keys show validator-wallet -a)
```

## Understanding Validator Parameters

Before creating your validator, understand the key parameters:

| Parameter | Description | Considerations |
|-----------|-------------|----------------|
| `moniker` | Your validator's display name | Choose something recognizable |
| `commission-rate` | Current commission percentage | Typically 5-10% for competitive validators |
| `commission-max-rate` | Maximum commission rate (cannot be changed after creation) | Set this thoughtfully; it is permanent |
| `commission-max-change-rate` | Maximum daily commission change | Limits how fast you can raise commission |
| `min-self-delegation` | Minimum tokens you must keep self-delegated | If your self-delegation drops below this, the validator is jailed |
| `details` | Description of your validator | Shown on block explorers |
| `website` | Your website URL | Shown on block explorers |
| `identity` | Keybase.io identity for avatar | 16-digit hex string from Keybase |
| `security-contact` | Email for security notifications | Recommended |

### Commission Rates

Commission is the percentage of delegator rewards that the validator keeps.

| Rate Type | Description | Example |
|-----------|-------------|---------|
| `commission-rate` | Starting commission rate | `0.05` (5%) |
| `commission-max-rate` | Lifetime maximum commission | `0.20` (20%) |
| `commission-max-change-rate` | Maximum daily rate change | `0.01` (1% per day) |

**Important:** `commission-max-rate` and `commission-max-change-rate` cannot be modified after the validator is created. Choose these values carefully.

## Create Validator Transaction

### Full Create-Validator Command

```bash
akash tx staking create-validator \
  --amount=1000000uakt \
  --pubkey=$(akash tendermint show-validator) \
  --moniker="My Akash Validator" \
  --details="A reliable validator for the Akash Network" \
  --website="https://myvalidator.example.com" \
  --identity="ABCDEF1234567890" \
  --security-contact="security@myvalidator.example.com" \
  --chain-id=akashnet-2 \
  --commission-rate="0.05" \
  --commission-max-rate="0.20" \
  --commission-max-change-rate="0.01" \
  --min-self-delegation="1" \
  --gas="auto" \
  --gas-adjustment=1.5 \
  --gas-prices="0.025uakt" \
  --from=validator-wallet \
  --node="http://localhost:26657" \
  -y
```

### Parameter Breakdown

| Flag | Value | Description |
|------|-------|-------------|
| `--amount` | `1000000uakt` | Self-delegation amount (1 AKT = 1,000,000 uakt) |
| `--pubkey` | Auto-detected | Validator's consensus public key |
| `--moniker` | `"My Akash Validator"` | Display name |
| `--details` | `"A reliable validator..."` | Description text |
| `--website` | URL | Validator website |
| `--identity` | Keybase identity | For avatar on block explorers |
| `--security-contact` | Email | Security contact email |
| `--chain-id` | `akashnet-2` | Akash mainnet chain ID |
| `--commission-rate` | `0.05` | 5% starting commission |
| `--commission-max-rate` | `0.20` | 20% maximum commission (permanent) |
| `--commission-max-change-rate` | `0.01` | 1% maximum daily change (permanent) |
| `--min-self-delegation` | `1` | Minimum 1 uakt self-delegation |
| `--gas` | `auto` | Automatically estimate gas |
| `--gas-adjustment` | `1.5` | Gas estimate multiplier for safety |
| `--gas-prices` | `0.025uakt` | Gas price |
| `--from` | `validator-wallet` | Wallet name to sign with |

## Verify Validator Creation

```bash
# Check if your validator is in the active set
akash query staking validator $(akash keys show validator-wallet --bech val -a)

# Check your validator's status
akash query staking validator $(akash keys show validator-wallet --bech val -a) --output json | jq '{
  moniker: .description.moniker,
  status: .status,
  jailed: .jailed,
  tokens: .tokens,
  commission_rate: .commission.commission_rates.rate,
  min_self_delegation: .min_self_delegation
}'
```

### Validator Status Values

| Status | Meaning |
|--------|---------|
| `BOND_STATUS_BONDED` | Active validator, participating in consensus |
| `BOND_STATUS_UNBONDING` | Unbonding, no longer in active set |
| `BOND_STATUS_UNBONDED` | Fully unbonded, not participating |

## Edit Validator Description

You can update your validator's description at any time (except `commission-max-rate` and `commission-max-change-rate`).

```bash
akash tx staking edit-validator \
  --moniker="Updated Validator Name" \
  --details="Updated description of my validator" \
  --website="https://new-website.example.com" \
  --identity="NEW_KEYBASE_ID" \
  --security-contact="new-security@example.com" \
  --chain-id=akashnet-2 \
  --gas="auto" \
  --gas-adjustment=1.5 \
  --gas-prices="0.025uakt" \
  --from=validator-wallet \
  -y
```

**Note:** Use `[do-not-modify]` as the value for any field you do not want to change:

```bash
# Only update the moniker, keep everything else the same
akash tx staking edit-validator \
  --moniker="New Name" \
  --details="[do-not-modify]" \
  --website="[do-not-modify]" \
  --identity="[do-not-modify]" \
  --chain-id=akashnet-2 \
  --gas="auto" \
  --gas-prices="0.025uakt" \
  --from=validator-wallet \
  -y
```

## Change Commission Rate

```bash
# Change commission rate (must be within max-change-rate per day)
akash tx staking edit-validator \
  --commission-rate="0.07" \
  --chain-id=akashnet-2 \
  --gas="auto" \
  --gas-adjustment=1.5 \
  --gas-prices="0.025uakt" \
  --from=validator-wallet \
  -y
```

**Constraints:**

- The new rate must not exceed `commission-max-rate`.
- The change from the current rate must not exceed `commission-max-change-rate`.
- Commission can only be changed once every 24 hours.

## Self-Delegation

### Add More Self-Delegation

```bash
# Delegate additional tokens to your own validator
akash tx staking delegate \
  $(akash keys show validator-wallet --bech val -a) \
  500000uakt \
  --chain-id=akashnet-2 \
  --gas="auto" \
  --gas-adjustment=1.5 \
  --gas-prices="0.025uakt" \
  --from=validator-wallet \
  -y
```

### Check Self-Delegation

```bash
# View your self-delegation
akash query staking delegation \
  $(akash keys show validator-wallet -a) \
  $(akash keys show validator-wallet --bech val -a)
```

### Unbond Self-Delegation

```bash
# Unbond tokens (subject to 21-day unbonding period)
akash tx staking unbond \
  $(akash keys show validator-wallet --bech val -a) \
  100000uakt \
  --chain-id=akashnet-2 \
  --gas="auto" \
  --gas-adjustment=1.5 \
  --gas-prices="0.025uakt" \
  --from=validator-wallet \
  -y
```

**Warning:** If your self-delegation drops below `min-self-delegation`, your validator will be jailed.

## Keybase Identity for Avatar

To display an avatar on block explorers, create a Keybase identity:

1. Create an account at [keybase.io](https://keybase.io).
2. Upload a profile picture.
3. Get your 16-digit identity string from your Keybase profile.
4. Use this string as the `--identity` flag when creating or editing your validator.

## Post-Creation Checklist

After creating your validator:

| Task | Command / Action |
|------|------------------|
| Verify validator is in active set | `akash query staking validators --status bonded -o json \| jq` |
| Set up monitoring | Configure alerts for downtime and missed blocks |
| Back up validator key | Securely store `~/.akash/config/priv_validator_key.json` |
| Back up mnemonic | Store wallet mnemonic in secure offline location |
| Configure sentry nodes | See [Validator Security](./security.md) |
| Set up TMKMS | See [Validator Security](./security.md) |
| Join validator channels | Join Akash Discord and validator communication channels |
| Set up cosmovisor | See [Validator Operations](./operations.md) |

## Important Warnings

- **Never run two nodes with the same validator key.** This will cause double-signing and result in permanent slashing (tombstoning).
- **Back up `priv_validator_key.json` securely.** Loss of this key means loss of your validator identity.
- **Monitor your validator continuously.** Extended downtime leads to jailing and slashing.
- **Keep your node software updated.** Missing chain upgrades will cause your node to halt and your validator to be jailed for downtime.
