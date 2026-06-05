# Lease Management

Managing active leases, monitoring deployments, and handling lease lifecycle.

## Viewing Leases

### List Active Leases

```bash
provider-services query market lease list --owner $(provider-services keys show wallet -a) --state active
```

### Get Specific Lease

```bash
provider-services query market lease get \
  --owner $(provider-services keys show wallet -a) \
  --dseq <DSEQ> \
  --gseq 1 \
  --oseq 1 \
  --provider <PROVIDER>
```

### Get Lease Status (from Provider)

```bash
provider-services lease-status \
  --dseq <DSEQ> \
  --gseq 1 \
  --oseq 1 \
  --provider <PROVIDER> \
  --from wallet
```

## Monitoring

### Service Health

```bash
# Check service availability
provider-services lease-status \
  --dseq <DSEQ> --gseq 1 --oseq 1 \
  --provider <PROVIDER> --from wallet | \
  jq '.services | to_entries[] | {name: .key, available: .value.available, total: .value.total}'
```

### View Logs

```bash
# All service logs
provider-services lease-logs \
  --dseq <DSEQ> --gseq 1 --oseq 1 \
  --provider <PROVIDER> --from wallet

# Specific service
provider-services lease-logs \
  --dseq <DSEQ> --gseq 1 --oseq 1 \
  --provider <PROVIDER> --from wallet \
  --service web

# Follow logs in real-time
provider-services lease-logs \
  --dseq <DSEQ> --gseq 1 --oseq 1 \
  --provider <PROVIDER> --from wallet \
  --follow --tail 100
```

### View Events

```bash
provider-services lease-events \
  --dseq <DSEQ> --gseq 1 --oseq 1 \
  --provider <PROVIDER> --from wallet
```

## Lease Operations

### Close Lease (Keep Deployment Open)

Close a single lease without closing the entire deployment:

```bash
provider-services tx market lease close \
  --dseq <DSEQ> \
  --gseq 1 \
  --oseq 1 \
  --from wallet
```

After closing, new bids will come in. Accept a new bid to create a fresh lease.

### Close Entire Deployment

Close deployment and all associated leases:

```bash
provider-services tx deployment close --dseq <DSEQ> --from wallet
```

### Migrate Provider

To move a deployment to a different provider:

```bash
# 1. Close current lease
provider-services tx market lease close \
  --dseq <DSEQ> --gseq 1 --oseq 1 --from wallet

# 2. Wait for new bids
sleep 30

# 3. List bids
provider-services query market bid list --owner $(provider-services keys show wallet -a) --dseq <DSEQ>

# 4. Accept new bid
provider-services tx market lease create \
  --dseq <DSEQ> --gseq 1 --oseq 2 \
  --provider <NEW_PROVIDER> --from wallet

# 5. Send manifest to new provider
provider-services send-manifest deploy.yaml \
  --dseq <DSEQ> --gseq 1 --oseq 2 \
  --provider <NEW_PROVIDER> --from wallet
```

Note: OSEQ increments when creating a new lease for the same group.

## Escrow Management

### Check Escrow Balance

```bash
provider-services query deployment get \
  --owner $(provider-services keys show wallet -a) \
  --dseq <DSEQ> | jq '.escrow_account'
```

### Deposit More Funds

```bash
provider-services tx deployment deposit 5000000uact --dseq <DSEQ> --from wallet
```

### Check Remaining Time

```bash
# Get current balance and price
BALANCE=$(provider-services query deployment get --owner $(provider-services keys show wallet -a) --dseq <DSEQ> -o json | jq -r '.escrow_account.balance.amount')
PRICE=$(provider-services query market lease get --owner $(provider-services keys show wallet -a) --dseq <DSEQ> --gseq 1 --oseq 1 --provider <PROVIDER> -o json | jq -r '.lease.price.amount')

echo "Blocks remaining: $(( $BALANCE / $PRICE ))"
echo "Hours remaining: $(( $BALANCE / $PRICE / 600 ))"
echo "Days remaining: $(( $BALANCE / $PRICE / 14400 ))"
```

## Interactive Shell

Access containers directly:

```bash
# Open shell
provider-services lease-shell \
  --dseq <DSEQ> --gseq 1 --oseq 1 \
  --provider <PROVIDER> --from wallet \
  --service web \
  -- /bin/sh

# Run specific command
provider-services lease-shell \
  --dseq <DSEQ> --gseq 1 --oseq 1 \
  --provider <PROVIDER> --from wallet \
  --service web \
  -- cat /etc/nginx/nginx.conf
```

## Troubleshooting

### Lease Not Active

```bash
# Check lease state
provider-services query market lease get --dseq <DSEQ> ... -o json | jq '.lease.state'
```

Possible states:
- `active` - Running normally
- `closed` - Terminated
- `insufficient_funds` - Escrow depleted

### Service Not Available

```bash
# Check events for errors
provider-services lease-events --dseq <DSEQ> ...

# Check logs for crash loops
provider-services lease-logs --dseq <DSEQ> ... --tail 50
```

### Cannot Send Manifest

- Verify certificate is active
- Check provider is online
- Wait and retry (provider may be processing)

### Escrow Depleted

```bash
# Deposit immediately
provider-services tx deployment deposit 10000000uact --dseq <DSEQ> --from wallet

# If deployment closed, create new one
provider-services tx deployment create deploy.yaml --from wallet
```

## Best Practices

1. **Monitor escrow** - Set up alerts before funds run out
2. **Use sufficient deposit** - Deposit at least 7 days worth
3. **Check logs regularly** - Catch issues early
4. **Keep SDL versioned** - Track changes to deployment config
5. **Test updates locally** - Validate SDL before updating
