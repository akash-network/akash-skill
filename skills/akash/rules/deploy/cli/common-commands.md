# CLI Command Reference

Quick reference for common Akash CLI commands.

## Configuration

There is no `config` subcommand. Configure defaults with environment variables and/or pass the corresponding flags (`--node`, `--chain-id`, `--keyring-backend`, `--gas-prices`) on each command.

```bash
# Set node
export AKASH_NODE=https://rpc.akashnet.net:443

# Set chain ID
export AKASH_CHAIN_ID=akashnet-2

# Set keyring backend
export AKASH_KEYRING_BACKEND=os

# Set gas prices
export AKASH_GAS_PRICES=0.025uakt
```

Or pass the equivalent flags per command:

```bash
provider-services <command> \
  --node https://rpc.akashnet.net:443 \
  --chain-id akashnet-2 \
  --keyring-backend os \
  --gas-prices 0.025uakt
```

## Keys (Wallet)

```bash
# Create wallet
provider-services keys add wallet

# Import from mnemonic
provider-services keys add wallet --recover

# List wallets
provider-services keys list

# Show address
provider-services keys show wallet -a

# Delete wallet
provider-services keys delete wallet

# Export key
provider-services keys export wallet > wallet.key
```

## Balance & Transfers

```bash
# Check balance
provider-services query bank balances <ADDRESS>

# Send tokens
provider-services tx bank send <FROM_ADDRESS> <TO_ADDRESS> 1000000uakt --from wallet
```

## Certificates

```bash
# Create certificate (two steps: generate then publish)
provider-services tx cert generate client --from wallet
provider-services tx cert publish client --from wallet

# List certificates
provider-services query cert list --owner <ADDRESS>

# Revoke certificate
provider-services tx cert revoke --from wallet
```

## Deployments

```bash
# Create deployment
provider-services tx deployment create deploy.yaml --from wallet

# Create with deposit
provider-services tx deployment create deploy.yaml --deposit 10000000uact --from wallet

# List deployments
provider-services query deployment list --owner <ADDRESS>

# Get deployment
provider-services query deployment get --owner <ADDRESS> --dseq <DSEQ>

# Update deployment
provider-services tx deployment update deploy.yaml --dseq <DSEQ> --from wallet

# Deposit funds
provider-services tx deployment deposit 5000000uact --dseq <DSEQ> --from wallet

# Close deployment
provider-services tx deployment close --dseq <DSEQ> --from wallet
```

## Market (Bids & Leases)

```bash
# List bids
provider-services query market bid list --owner <ADDRESS> --dseq <DSEQ>

# Create lease (accept bid)
provider-services tx market lease create \
  --dseq <DSEQ> \
  --gseq 1 \
  --oseq 1 \
  --provider <PROVIDER> \
  --from wallet

# List leases
provider-services query market lease list --owner <ADDRESS>

# Get lease
provider-services query market lease get \
  --owner <ADDRESS> \
  --dseq <DSEQ> \
  --gseq 1 \
  --oseq 1 \
  --provider <PROVIDER>

# Close lease
provider-services tx market lease close \
  --dseq <DSEQ> \
  --gseq 1 \
  --oseq 1 \
  --from wallet
```

## Provider Operations

```bash
# Send manifest
provider-services send-manifest deploy.yaml \
  --dseq <DSEQ> \
  --gseq 1 \
  --oseq 1 \
  --provider <PROVIDER> \
  --from wallet

# Lease status
provider-services lease-status \
  --dseq <DSEQ> \
  --gseq 1 \
  --oseq 1 \
  --provider <PROVIDER> \
  --from wallet

# Lease logs
provider-services lease-logs \
  --dseq <DSEQ> \
  --gseq 1 \
  --oseq 1 \
  --provider <PROVIDER> \
  --from wallet

# Follow logs
provider-services lease-logs \
  --dseq <DSEQ> \
  --gseq 1 \
  --oseq 1 \
  --provider <PROVIDER> \
  --from wallet \
  --follow

# Specific service logs
provider-services lease-logs \
  --dseq <DSEQ> \
  --gseq 1 \
  --oseq 1 \
  --provider <PROVIDER> \
  --from wallet \
  --service web

# Interactive shell
provider-services lease-shell \
  --dseq <DSEQ> \
  --gseq 1 \
  --oseq 1 \
  --provider <PROVIDER> \
  --from wallet \
  --service web \
  -- /bin/sh

# Events
provider-services lease-events \
  --dseq <DSEQ> \
  --gseq 1 \
  --oseq 1 \
  --provider <PROVIDER> \
  --from wallet
```

## Queries

```bash
# Network status
provider-services status

# Current block height
provider-services query block

# Provider list
provider-services query provider list

# Provider details
provider-services query provider get <PROVIDER_ADDRESS>

# Auditor list
provider-services query audit list
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
alias akaddr='provider-services keys show wallet -a'

# Quick balance
alias akbal='provider-services query bank balances $(provider-services keys show wallet -a)'

# List my deployments
alias akdeps='provider-services query deployment list --owner $(provider-services keys show wallet -a)'

# List my leases
alias akleases='provider-services query market lease list --owner $(provider-services keys show wallet -a)'

# Quick deploy
akdeploy() {
  provider-services tx deployment create "$1" --from wallet -y
}

# Quick close
akclose() {
  provider-services tx deployment close --dseq "$1" --from wallet -y
}
```

## Output Parsing

```bash
# Get address
ADDRESS=$(provider-services keys show wallet -a)

# Get deployment dseq from create
DSEQ=$(provider-services tx deployment create deploy.yaml --from wallet -y --output json | jq -r '.events[] | select(.type=="akash.v1") | .attributes[] | select(.key=="dseq") | .value')

# Get first provider from bids
PROVIDER=$(provider-services query market bid list --owner $ADDRESS --dseq $DSEQ --output json | jq -r '.bids[0].bid.id.provider')

# Get service URIs
provider-services lease-status ... --output json | jq -r '.services.web.uris[]'
```

## Debug Options

```bash
# Verbose output
provider-services tx deployment create deploy.yaml --from wallet --log_level debug

# Dry run (simulate)
provider-services tx deployment create deploy.yaml --from wallet --dry-run

# Print transaction without broadcasting
provider-services tx deployment create deploy.yaml --from wallet --generate-only
```

## Help

```bash
# General help
provider-services --help

# Command help
provider-services tx deployment --help
provider-services tx deployment create --help

# Query help
provider-services query --help
provider-services query deployment --help
```
