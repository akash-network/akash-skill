# CLI Command Reference

Quick reference for common Akash CLI commands.

## Configuration

```bash
# Set node
akash config node https://rpc.akashnet.net:443

# Set chain ID
akash config chain-id akashnet-2

# Set keyring
akash config keyring-backend os

# View config
akash config
```

## Keys (Wallet)

```bash
# Create wallet
akash keys add wallet

# Import from mnemonic
akash keys add wallet --recover

# List wallets
akash keys list

# Show address
akash keys show wallet -a

# Delete wallet
akash keys delete wallet

# Export key
akash keys export wallet > wallet.key
```

## Balance & Transfers

```bash
# Check balance
akash query bank balances <ADDRESS>

# Send tokens
akash tx bank send <FROM_ADDRESS> <TO_ADDRESS> 1000000uact --from wallet
```

## Certificates

```bash
# Create certificate
akash tx cert create client --from wallet

# List certificates
akash query cert list --owner <ADDRESS>

# Revoke certificate
akash tx cert revoke --from wallet
```

## Deployments

```bash
# Create deployment
akash tx deployment create deploy.yaml --from wallet

# Create with deposit
akash tx deployment create deploy.yaml --deposit 10000000uact --from wallet

# List deployments
akash query deployment list --owner <ADDRESS>

# Get deployment
akash query deployment get --owner <ADDRESS> --dseq <DSEQ>

# Update deployment
akash tx deployment update deploy.yaml --dseq <DSEQ> --from wallet

# Deposit funds
akash tx deployment deposit 5000000uact --dseq <DSEQ> --from wallet

# Close deployment
akash tx deployment close --dseq <DSEQ> --from wallet
```

## Market (Bids & Leases)

```bash
# List bids
akash query market bid list --owner <ADDRESS> --dseq <DSEQ>

# Create lease (accept bid)
akash tx market lease create \
  --dseq <DSEQ> \
  --gseq 1 \
  --oseq 1 \
  --provider <PROVIDER> \
  --from wallet

# List leases
akash query market lease list --owner <ADDRESS>

# Get lease
akash query market lease get \
  --owner <ADDRESS> \
  --dseq <DSEQ> \
  --gseq 1 \
  --oseq 1 \
  --provider <PROVIDER>

# Close lease
akash tx market lease close \
  --dseq <DSEQ> \
  --gseq 1 \
  --oseq 1 \
  --from wallet
```

## Provider Operations

```bash
# Send manifest
akash provider send-manifest deploy.yaml \
  --dseq <DSEQ> \
  --gseq 1 \
  --oseq 1 \
  --provider <PROVIDER> \
  --from wallet

# Lease status
akash provider lease-status \
  --dseq <DSEQ> \
  --gseq 1 \
  --oseq 1 \
  --provider <PROVIDER> \
  --from wallet

# Lease logs
akash provider lease-logs \
  --dseq <DSEQ> \
  --gseq 1 \
  --oseq 1 \
  --provider <PROVIDER> \
  --from wallet

# Follow logs
akash provider lease-logs \
  --dseq <DSEQ> \
  --gseq 1 \
  --oseq 1 \
  --provider <PROVIDER> \
  --from wallet \
  --follow

# Specific service logs
akash provider lease-logs \
  --dseq <DSEQ> \
  --gseq 1 \
  --oseq 1 \
  --provider <PROVIDER> \
  --from wallet \
  --service web

# Interactive shell
akash provider lease-shell \
  --dseq <DSEQ> \
  --gseq 1 \
  --oseq 1 \
  --provider <PROVIDER> \
  --from wallet \
  --service web \
  -- /bin/sh

# Events
akash provider lease-events \
  --dseq <DSEQ> \
  --gseq 1 \
  --oseq 1 \
  --provider <PROVIDER> \
  --from wallet
```

## Queries

```bash
# Network status
akash status

# Current block height
akash query block

# Provider list
akash query provider list

# Provider details
akash query provider get <PROVIDER_ADDRESS>

# Auditor list
akash query audit list
```

## Transaction Flags

Common flags for transactions:

```bash
# Auto gas estimation
--gas auto

# Gas adjustment
--gas-adjustment 1.5

# Explicit gas
--gas 200000

# Gas prices
--gas-prices 0.025uakt

# Skip confirmation
-y

# Output format
--output json

# Broadcast mode
--broadcast-mode sync  # or async, block
```

## Environment Variables

```bash
export AKASH_NODE="https://rpc.akashnet.net:443"
export AKASH_CHAIN_ID="akashnet-2"
export AKASH_KEYRING_BACKEND="os"
export AKASH_FROM="wallet"
export AKASH_GAS="auto"
export AKASH_GAS_ADJUSTMENT="1.5"
export AKASH_GAS_PRICES="0.025uakt"
export AKASH_OUTPUT="json"
```

## Shortcut Aliases

Add to `~/.bashrc` or `~/.zshrc`:

```bash
# Quick address
alias akaddr='akash keys show wallet -a'

# Quick balance
alias akbal='akash query bank balances $(akash keys show wallet -a)'

# List my deployments
alias akdeps='akash query deployment list --owner $(akash keys show wallet -a)'

# List my leases
alias akleases='akash query market lease list --owner $(akash keys show wallet -a)'

# Quick deploy
akdeploy() {
  akash tx deployment create "$1" --from wallet -y
}

# Quick close
akclose() {
  akash tx deployment close --dseq "$1" --from wallet -y
}
```

## Output Parsing

```bash
# Get address
ADDRESS=$(akash keys show wallet -a)

# Get deployment dseq from create
DSEQ=$(akash tx deployment create deploy.yaml --from wallet -y --output json | jq -r '.logs[0].events[] | select(.type=="akash.v1") | .attributes[] | select(.key=="dseq") | .value')

# Get first provider from bids
PROVIDER=$(akash query market bid list --owner $ADDRESS --dseq $DSEQ --output json | jq -r '.bids[0].bid.bid_id.provider')

# Get service URIs
akash provider lease-status ... --output json | jq -r '.services.web.uris[]'
```

## Debug Options

```bash
# Verbose output
akash tx deployment create deploy.yaml --from wallet --log_level debug

# Dry run (simulate)
akash tx deployment create deploy.yaml --from wallet --dry-run

# Print transaction without broadcasting
akash tx deployment create deploy.yaml --from wallet --generate-only
```

## Help

```bash
# General help
akash --help

# Command help
akash tx deployment --help
akash tx deployment create --help

# Query help
akash query --help
akash query deployment --help
```
