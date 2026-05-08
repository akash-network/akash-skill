# Managed Wallet Operations

The Console API provides managed wallet functionality for simplified deployment without handling private keys.

## Overview

Managed wallets allow you to:

- Deploy without managing private keys
- Fund deployments via deposit address
- Automatic transaction signing
- Simplified escrow management

## Wallet Operations

### Create Managed Wallet

Create a new managed wallet for your account:

```bash
curl -X POST https://console-api.akash.network/v1/wallet/create \
  -H "Authorization: Bearer <api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "production-wallet"
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "wallet-123",
    "name": "production-wallet",
    "address": "akash1abc...",
    "createdAt": "2024-01-15T10:00:00Z"
  }
}
```

### Get Wallet Balance

Check your managed wallet balance:

```bash
curl https://console-api.akash.network/v1/wallet/balance \
  -H "Authorization: Bearer <api-key>"
```

**Response:**
```json
{
  "success": true,
  "data": {
    "address": "akash1abc...",
    "balances": [
      {
        "denom": "uact",
        "amount": "10000000"
      },
      {
        "denom": "ibc/170C677610AC31DF0904FFE09CD3B5C657492170E7E52372E48756B71E56F2F1",
        "amount": "5000000"
      }
    ]
  }
}
```

### Get Deposit Address

Get address for funding your managed wallet:

```bash
curl -X POST https://console-api.akash.network/v1/wallet/deposit \
  -H "Authorization: Bearer <api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "denom": "uact"
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "address": "akash1abc...",
    "memo": "deposit-12345",
    "minimumDeposit": "1000000",
    "denom": "uact"
  }
}
```

### List Wallets

Get all managed wallets:

```bash
curl https://console-api.akash.network/v1/wallet/list \
  -H "Authorization: Bearer <api-key>"
```

**Response:**
```json
{
  "success": true,
  "data": {
    "wallets": [
      {
        "id": "wallet-123",
        "name": "production-wallet",
        "address": "akash1abc...",
        "isDefault": true
      },
      {
        "id": "wallet-456",
        "name": "staging-wallet",
        "address": "akash1def...",
        "isDefault": false
      }
    ]
  }
}
```

### Set Default Wallet

Set which wallet to use for deployments:

```bash
curl -X POST https://console-api.akash.network/v1/wallet/default \
  -H "Authorization: Bearer <api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "walletId": "wallet-456"
  }'
```

## Funding Managed Wallets

### Via Exchange

1. Get deposit address from Console API
2. Withdraw AKT/USDC from exchange to that address
3. Include memo if provided
4. Wait for confirmation

### Via IBC Transfer

Transfer tokens from another Cosmos chain:

```bash
# Example: Transfer from Osmosis
osmosisd tx ibc-transfer transfer \
  transfer channel-1 \
  <akash-managed-wallet-address> \
  1000000uosmo \
  --from wallet
```

### Via Another Wallet

Send from your personal wallet:

```bash
akash tx bank send \
  <your-address> \
  <managed-wallet-address> \
  10000000uact \
  --from wallet
```

## Deploying with Managed Wallet

### Create Deployment

```bash
curl -X POST https://console-api.akash.network/v1/deployment \
  -H "Authorization: Bearer <api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "sdl": "<your-sdl>",
    "deposit": "5000000uact",
    "walletId": "wallet-123"
  }'
```

The API automatically:
1. Creates deployment transaction
2. Signs with managed wallet
3. Broadcasts to network
4. Returns deployment ID

### Accept Bid

```bash
curl -X POST https://console-api.akash.network/v1/lease \
  -H "Authorization: Bearer <api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "dseq": "<dseq>",
    "gseq": 1,
    "oseq": 1,
    "provider": "<provider-address>",
    "walletId": "wallet-123"
  }'
```

### Add Funds to Deployment

```bash
curl -X POST https://console-api.akash.network/v1/deployment/<dseq>/deposit \
  -H "Authorization: Bearer <api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": "5000000uact",
    "walletId": "wallet-123"
  }'
```

## Automation Example

Complete deployment workflow:

```typescript
const API_KEY = process.env.AKASH_API_KEY;
const API_URL = 'https://console-api.akash.network/v1';

async function deployWithManagedWallet(sdl: string) {
  // Check wallet balance
  const balanceRes = await fetch(`${API_URL}/wallet/balance`, {
    headers: { 'Authorization': `Bearer ${API_KEY}` }
  });
  const { data: { balances } } = await balanceRes.json();

  const aktBalance = balances.find(b => b.denom === 'uact')?.amount || '0';
  if (BigInt(aktBalance) < BigInt('5000000')) {
    throw new Error('Insufficient balance');
  }

  // Create deployment
  const deployRes = await fetch(`${API_URL}/deployment`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${API_KEY}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      sdl,
      deposit: '5000000uact'
    })
  });
  const { data: { dseq } } = await deployRes.json();

  console.log(`Deployment created: ${dseq}`);

  // Wait for bids
  await new Promise(r => setTimeout(r, 30000));

  // Get bids
  const bidsRes = await fetch(`${API_URL}/bids/${dseq}`, {
    headers: { 'Authorization': `Bearer ${API_KEY}` }
  });
  const { data: bids } = await bidsRes.json();

  if (bids.length === 0) {
    throw new Error('No bids received');
  }

  // Accept lowest bid
  const lowestBid = bids.sort((a, b) =>
    Number(a.price.amount) - Number(b.price.amount)
  )[0];

  const leaseRes = await fetch(`${API_URL}/lease`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${API_KEY}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      dseq,
      gseq: 1,
      oseq: 1,
      provider: lowestBid.provider
    })
  });
  const { data: lease } = await leaseRes.json();

  console.log(`Lease created with provider: ${lease.provider}`);

  return { dseq, lease };
}
```

## Security Considerations

### Managed Wallet Security

- Keys are encrypted and stored securely
- Console never exposes private keys
- Transactions require API authentication
- Audit logs track all operations

### Best Practices

1. **Use separate wallets** for different environments
2. **Monitor balances** to prevent deployment failures
3. **Set up alerts** for low balance notifications
4. **Review transactions** in Console dashboard

### Limitations

- Cannot export private keys
- Withdrawals require additional verification
- Subject to Console API availability
- Rate limits apply

## Troubleshooting

### Insufficient Balance

```json
{
  "error": {
    "code": "INSUFFICIENT_BALANCE",
    "message": "Wallet has insufficient funds",
    "required": "5000000",
    "available": "1000000"
  }
}
```

**Solution:** Fund the wallet before deployment.

### Wallet Not Found

```json
{
  "error": {
    "code": "WALLET_NOT_FOUND",
    "message": "Wallet with id 'wallet-999' not found"
  }
}
```

**Solution:** Check wallet ID or use default wallet.

### Transaction Failed

```json
{
  "error": {
    "code": "TRANSACTION_FAILED",
    "message": "Transaction failed: out of gas",
    "txHash": "ABC123..."
  }
}
```

**Solution:** Check transaction on block explorer for details.
