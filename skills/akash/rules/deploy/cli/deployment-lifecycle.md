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
provider-services version

# Check wallet
provider-services keys show wallet -a

# Check balance (need ~5 AKT minimum)
provider-services query bank balances $(provider-services keys show wallet -a)
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

Generate and broadcast client certificate (two steps):

```bash
provider-services tx cert generate client --from wallet
provider-services tx cert publish client --from wallet
```

Verify certificate:

```bash
provider-services query cert list --owner $(provider-services keys show wallet -a)
```

## Step 3: Create Deployment

```bash
provider-services tx deployment create deploy.yaml --from wallet
```

Capture the deployment sequence (dseq) from output:

```bash
# Or query your deployments
provider-services query deployment list --owner $(provider-services keys show wallet -a)
```

### With Explicit Deposit

```bash
provider-services tx deployment create deploy.yaml --deposit 10000000uact --from wallet
```

## Step 4: Wait for Bids

Query bids for your deployment:

```bash
provider-services query market bid list --owner $(provider-services keys show wallet -a) --dseq <DSEQ>
```

Wait until bids appear (usually 15-60 seconds).

Example output:
```json
{
  "bids": [
    {
      "bid": {
        "id": {
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
provider-services tx market lease create \
  --dseq <DSEQ> \
  --gseq 1 \
  --oseq 1 \
  --provider <PROVIDER_ADDRESS> \
  --from wallet
```

Verify lease:

```bash
provider-services query market lease list --owner $(provider-services keys show wallet -a) --dseq <DSEQ>
```

## Step 6: Send Manifest

```bash
provider-services send-manifest deploy.yaml \
  --dseq <DSEQ> \
  --gseq 1 \
  --oseq 1 \
  --provider <PROVIDER_ADDRESS> \
  --from wallet
```

## Step 7: Access Deployment

### Get Lease Status

```bash
provider-services lease-status \
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
provider-services lease-logs \
  --dseq <DSEQ> \
  --gseq 1 \
  --oseq 1 \
  --provider <PROVIDER_ADDRESS> \
  --from wallet
```

### Follow Logs

```bash
provider-services lease-logs \
  --dseq <DSEQ> \
  --gseq 1 \
  --oseq 1 \
  --provider <PROVIDER_ADDRESS> \
  --from wallet \
  --follow
```

### Interactive Shell

```bash
provider-services lease-shell \
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
provider-services tx deployment close --dseq <DSEQ> --from wallet
```

Verify closed:

```bash
provider-services query deployment get --owner $(provider-services keys show wallet -a) --dseq <DSEQ>
```

## Resource Reclamation Lifecycle (v2.1.0+)

When a deployment declares a [`reclamation` block](../../sdl/reclamation.md), a
**provider** may reclaim the lease's resources — but only after honoring the
tenant's grace window. This is opt-in: deployments without a `reclamation` block,
and all SDL 2.0 deployments, never enter this flow.

```
Active ──MsgLeaseStartReclaim (provider)──▶ Reclaiming
                                              │  deadline = block_time + window
                                              │
   provider close BEFORE deadline ──▶ rejected
   provider close AFTER  deadline ──▶ group PAUSED (no auto-re-order)
```

1. **Provider starts reclamation** — the provider signs `MsgLeaseStartReclaim` on an
   `Active` lease with a `reason` (a `LeaseClosedReason` in the provider range
   10000–19999). The lease moves to `Reclaiming` and a deadline is set at
   `block_time + window`.
2. **Tenant reacts within the window** — drain, snapshot, or migrate. The provider
   **cannot** close the lease before the deadline; an early close is rejected.
3. **After the deadline** — the provider may close the lease. The group is left
   **paused**: there is **no automatic re-order**. Recover by resuming the group
   (`MsgStartGroup`) or by closing and redeploying.

### Tenant-initiated vs provider-initiated close

| Action | Effect |
|--------|--------|
| `MsgLeaseStartReclaim` (provider) | Starts the window; close only allowed after the deadline; post-deadline close pauses the group. |
| `MsgCloseLease` (tenant, single lease) | Allowed anytime; **auto-re-orders** — the new order inherits the deployment's reclamation requirement. |
| `MsgCloseDeployment` (tenant, whole deployment) | Escrow-level close; **bypasses** the reclamation window. |

### Recovering a paused group

A paused group does not re-order on its own. Resume it with `MsgStartGroup` (new
orders inherit the reclamation requirement), or close the deployment and redeploy.
Reclamation of a lease is terminal — there is no "restart" of the reclaimed lease
itself.

See [terminology.md](../../terminology.md#resource-reclamation-aep-82) for the
message and state glossary.

## Managing Deployments

### Add Funds

```bash
provider-services tx deployment deposit 5000000uact --dseq <DSEQ> --from wallet
```

### Update Deployment

```bash
provider-services tx deployment update deploy-updated.yaml --dseq <DSEQ> --from wallet
```

Then send updated manifest:

```bash
provider-services send-manifest deploy-updated.yaml \
  --dseq <DSEQ> \
  --gseq 1 \
  --oseq 1 \
  --provider <PROVIDER_ADDRESS> \
  --from wallet
```

### Close Specific Lease

```bash
provider-services tx market lease close \
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
ADDRESS=$(provider-services keys show $WALLET -a)

# Create deployment
echo "Creating deployment..."
TX_RESULT=$(provider-services tx deployment create $SDL_FILE --from $WALLET -y --output json)
DSEQ=$(echo $TX_RESULT | jq -r '.events[] | select(.type=="akash.v1") | .attributes[] | select(.key=="dseq") | .value')

echo "Deployment DSEQ: $DSEQ"

# Wait for bids
echo "Waiting for bids..."
sleep 30

# Get first bid
BID=$(provider-services query market bid list --owner $ADDRESS --dseq $DSEQ --output json | jq -r '.bids[0]')
PROVIDER=$(echo $BID | jq -r '.bid.id.provider')

echo "Selected provider: $PROVIDER"

# Create lease
echo "Creating lease..."
provider-services tx market lease create \
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
provider-services send-manifest $SDL_FILE \
  --dseq $DSEQ \
  --gseq 1 \
  --oseq 1 \
  --provider $PROVIDER \
  --from $WALLET

# Wait for deployment
sleep 15

# Get status
echo "Getting status..."
provider-services lease-status \
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
provider-services lease-status --dseq <DSEQ> ...

# Check logs for errors
provider-services lease-logs --dseq <DSEQ> ...
```

### Escrow Depleted

```bash
# Check escrow balance
provider-services query deployment get --dseq <DSEQ> --owner $(provider-services keys show wallet -a)

# Deposit more funds
provider-services tx deployment deposit 5000000uact --dseq <DSEQ> --from wallet
```
