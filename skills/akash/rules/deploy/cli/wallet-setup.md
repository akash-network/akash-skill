# Wallet Setup

Create and manage wallets for Akash CLI operations.

## Create New Wallet

### Generate New Key

```bash
akash keys add wallet
```

Output:
```
- address: akash1abc123...
  name: wallet
  pubkey: '{"@type":"/cosmos.crypto.secp256k1.PubKey","key":"..."}'
  type: local

**Important** write this mnemonic phrase in a safe place.
It is the only way to recover your account if you ever forget your password.

word1 word2 word3 ... word24
```

**Save the mnemonic phrase securely!**

### With Custom Name

```bash
akash keys add production-wallet
akash keys add staging-wallet
```

## Import Existing Wallet

### From Mnemonic

```bash
akash keys add wallet --recover
```

Enter your 24-word mnemonic when prompted.

### From Keystore File

```bash
akash keys import wallet keyfile.json
```

### From Ledger

```bash
akash keys add wallet --ledger
```

## List Wallets

```bash
akash keys list
```

Output:
```json
[
  {
    "name": "wallet",
    "type": "local",
    "address": "akash1abc123...",
    "pubkey": "{...}"
  }
]
```

## Show Wallet Details

```bash
akash keys show wallet
```

### Show Address Only

```bash
akash keys show wallet -a
```

### Show Public Key Only

```bash
akash keys show wallet --pubkey
```

## Delete Wallet

```bash
akash keys delete wallet
```

**Warning:** This removes the key from your keyring. Ensure you have the mnemonic backed up.

## Export Wallet

### Export Private Key (Encrypted)

```bash
akash keys export wallet > wallet.key
```

### Export Unencrypted (Dangerous)

```bash
akash keys unsafe-export-eth-key wallet
```

**Only use for specific integrations. Never share this key.**

## Fund Wallet

### Check Balance

```bash
akash query bank balances $(akash keys show wallet -a)
```

### Get Tokens

1. **Purchase AKT** from exchanges (Kraken, Coinbase, etc.)
2. **Withdraw to your address** shown by `akash keys show wallet -a`
3. **Or use testnet faucet** for sandbox network

### Verify Funds

```bash
akash query bank balances $(akash keys show wallet -a) --node https://rpc.akashnet.net:443
```

## Multiple Wallets

### Use Different Keys

```bash
# Default wallet
akash tx bank send ... --from wallet

# Specific wallet
akash tx bank send ... --from production-wallet
```

### Environment Variable

```bash
export AKASH_FROM=wallet
akash tx deployment create deploy.yaml  # Uses $AKASH_FROM
```

## Security Best Practices

### Keyring Backends

| Backend | Security | Use Case |
|---------|----------|----------|
| `os` | High | Production (uses OS keychain) |
| `file` | Medium | Servers (encrypted file) |
| `test` | Low | Development only |

```bash
# Production
akash config keyring-backend os

# Server deployment
akash config keyring-backend file

# Development
akash config keyring-backend test
```

### Password Management

With `os` or `file` backend, you'll be prompted for password:

```bash
akash keys add wallet --keyring-backend file
# Enter and confirm password
```

For scripting, use environment:

```bash
export AKASH_KEYRING_BACKEND=file
echo "password" | akash tx deployment create deploy.yaml --from wallet
```

### Hardware Wallets

For maximum security, use Ledger:

```bash
# Create Ledger-backed key
akash keys add wallet --ledger

# Sign transaction (requires physical confirmation)
akash tx deployment create deploy.yaml --from wallet --ledger
```

## Wallet Permissions

### Query Operations (No Key Needed)

```bash
# Anyone can query
akash query deployment list --owner akash1abc...
```

### Transaction Operations (Key Required)

```bash
# Requires key for signing
akash tx deployment create deploy.yaml --from wallet
```

## Troubleshooting

### Key Not Found

```bash
Error: wallet.info: key not found
```

**Solution:** Check keyring backend matches where key was created:

```bash
akash keys list --keyring-backend os
akash keys list --keyring-backend test
```

### Wrong Password

```bash
Error: invalid passphrase
```

**Solution:** Re-enter correct password or recover from mnemonic:

```bash
akash keys delete wallet
akash keys add wallet --recover
```

### Insufficient Funds

```bash
Error: insufficient funds
```

**Solution:** Check balance and fund wallet:

```bash
akash query bank balances $(akash keys show wallet -a)
# Fund from exchange or transfer from another wallet
```

## Address Derivation

Akash uses standard Cosmos SDK derivation:

```
HD Path: m/44'/118'/0'/0/0
Prefix: akash
```

You can derive multiple accounts:

```bash
# Account 0 (default)
akash keys add wallet

# Account 1
akash keys add wallet2 --account 1

# Account 2
akash keys add wallet3 --account 2
```

## Next Steps

- **@deployment-lifecycle.md** - Create deployments
- **@common-commands.md** - Command reference
