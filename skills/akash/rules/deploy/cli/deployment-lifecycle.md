# Deployment Lifecycle

Complete guide to creating, managing, and closing deployments via CLI.

## Deployment Flow Overview

```
1. Create SDL file
2. Create certificate (first time)
3. Create deployment
4. Wait for bids
5. Accept bid (create lease)
6. Send manifest
7. Access deployment
8. Close deployment (when done)
```

## Prerequisites

```bash
# Verify CLI setup
akash version

# Check wallet
akash keys show wallet -a

# Check balance (need ~5 AKT minimum)
akash query bank balances $(akash keys show wallet -a)
```

## Step 1: Create SDL File

Create `deploy.yaml`:

```yaml
version: "2.0"

services:
  web:
    image: nginx:1.25.3
    expose:
      - port: 80
        as: 80
        to:
          - global: true

profiles:
  compute:
    web:
      resources:
        cpu:
          units: 0.5
        memory:
          size: 512Mi
        storage:
          size: 1Gi
  placement:
    dcloud:
      pricing:
        web:
          denom: uact
          amount: 1000

deployment:
  web:
    dcloud:
      profile: web
      count: 1
```

## Step 2: Create Certificate (First Time Only)

Generate and broadcast client certificate:

```bash
akash tx cert create client --from wallet
```

Verify certificate:

```bash
akash query cert list --owner $(akash keys show wallet -a)
```

## Step 3: Create Deployment

```bash
akash tx deployment create deploy.yaml --from wallet
```

Capture the deployment sequence (dseq) from output:

```bash
# Or query your deployments
akash query deployment list --owner $(akash keys show wallet -a)
```

### With Explicit Deposit

```bash
akash tx deployment create deploy.yaml --deposit 10000000uact --from wallet
```

## Step 4: Wait for Bids

Query bids for your deployment:

```bash
akash query market bid list --owner $(akash keys show wallet -a) --dseq <DSEQ>
```

Wait until bids appear (usually 15-60 seconds).

Example output:
```json
{
  "bids": [
    {
      "bid": {
        "bid_id": {
          "owner": "akash1...",
          "dseq": "12345678",
          "gseq": 1,
          "oseq": 1,
          "provider": "akash1provider..."
        },
        "price": {
          "denom": "uact",
          "amount": "950"
        },
        "state": "open"
      }
    }
  ]
}
```

## Step 5: Accept Bid (Create Lease)

```bash
akash tx market lease create \
  --dseq <DSEQ> \
  --gseq 1 \
  --oseq 1 \
  --provider <PROVIDER_ADDRESS> \
  --from wallet
```

Verify lease:

```bash
akash query market lease list --owner $(akash keys show wallet -a) --dseq <DSEQ>
```

## Step 6: Send Manifest

```bash
akash provider send-manifest deploy.yaml \
  --dseq <DSEQ> \
  --gseq 1 \
  --oseq 1 \
  --provider <PROVIDER_ADDRESS> \
  --from wallet
```

## Step 7: Access Deployment

### Get Lease Status

```bash
akash provider lease-status \
  --dseq <DSEQ> \
  --gseq 1 \
  --oseq 1 \
  --provider <PROVIDER_ADDRESS> \
  --from wallet
```

Output includes service URIs:

```json
{
  "services": {
    "web": {
      "name": "web",
      "available": 1,
      "total": 1,
      "uris": [
        "abc123.provider.akash.network"
      ]
    }
  }
}
```

### Get Logs

```bash
akash provider lease-logs \
  --dseq <DSEQ> \
  --gseq 1 \
  --oseq 1 \
  --provider <PROVIDER_ADDRESS> \
  --from wallet
```

### Follow Logs

```bash
akash provider lease-logs \
  --dseq <DSEQ> \
  --gseq 1 \
  --oseq 1 \
  --provider <PROVIDER_ADDRESS> \
  --from wallet \
  --follow
```

### Interactive Shell

```bash
akash provider lease-shell \
  --dseq <DSEQ> \
  --gseq 1 \
  --oseq 1 \
  --provider <PROVIDER_ADDRESS> \
  --from wallet \
  --service web \
  -- /bin/sh
```

## Step 8: Close Deployment

When done, close to stop billing and reclaim escrow:

```bash
akash tx deployment close --dseq <DSEQ> --from wallet
```

Verify closed:

```bash
akash query deployment get --owner $(akash keys show wallet -a) --dseq <DSEQ>
```

## Managing Deployments

### Add Funds

```bash
akash tx deployment deposit 5000000uact --dseq <DSEQ> --from wallet
```

### Update Deployment

```bash
akash tx deployment update deploy-updated.yaml --dseq <DSEQ> --from wallet
```

Then send updated manifest:

```bash
akash provider send-manifest deploy-updated.yaml \
  --dseq <DSEQ> \
  --gseq 1 \
  --oseq 1 \
  --provider <PROVIDER_ADDRESS> \
  --from wallet
```

### Close Specific Lease

```bash
akash tx market lease close \
  --dseq <DSEQ> \
  --gseq 1 \
  --oseq 1 \
  --from wallet
```

## Scripting Deployments

### Bash Script Example

```bash
#!/bin/bash
set -e

SDL_FILE="deploy.yaml"
WALLET="wallet"

# Get address
ADDRESS=$(akash keys show $WALLET -a)

# Create deployment
echo "Creating deployment..."
TX_RESULT=$(akash tx deployment create $SDL_FILE --from $WALLET -y --output json)
DSEQ=$(echo $TX_RESULT | jq -r '.logs[0].events[] | select(.type=="akash.v1") | .attributes[] | select(.key=="dseq") | .value')

echo "Deployment DSEQ: $DSEQ"

# Wait for bids
echo "Waiting for bids..."
sleep 30

# Get first bid
BID=$(akash query market bid list --owner $ADDRESS --dseq $DSEQ --output json | jq -r '.bids[0]')
PROVIDER=$(echo $BID | jq -r '.bid.bid_id.provider')

echo "Selected provider: $PROVIDER"

# Create lease
echo "Creating lease..."
akash tx market lease create \
  --dseq $DSEQ \
  --gseq 1 \
  --oseq 1 \
  --provider $PROVIDER \
  --from $WALLET \
  -y

# Wait for lease
sleep 10

# Send manifest
echo "Sending manifest..."
akash provider send-manifest $SDL_FILE \
  --dseq $DSEQ \
  --gseq 1 \
  --oseq 1 \
  --provider $PROVIDER \
  --from $WALLET

# Wait for deployment
sleep 15

# Get status
echo "Getting status..."
akash provider lease-status \
  --dseq $DSEQ \
  --gseq 1 \
  --oseq 1 \
  --provider $PROVIDER \
  --from $WALLET

echo "Deployment complete! DSEQ: $DSEQ"
```

## Troubleshooting

### No Bids Received

- Check pricing in SDL (may be too low)
- Verify SDL syntax
- Check provider availability

### Manifest Send Failed

- Verify certificate is valid
- Check provider is online
- Retry after a few seconds

### Deployment Not Starting

```bash
# Check lease status
akash provider lease-status --dseq <DSEQ> ...

# Check logs for errors
akash provider lease-logs --dseq <DSEQ> ...
```

### Escrow Depleted

```bash
# Check escrow balance
akash query deployment get --dseq <DSEQ> --owner $(akash keys show wallet -a)

# Deposit more funds
akash tx deployment deposit 5000000uact --dseq <DSEQ> --from wallet
```
