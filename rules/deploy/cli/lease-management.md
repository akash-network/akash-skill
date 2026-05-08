# Lease Management

Managing active leases, monitoring deployments, and handling lease lifecycle.

## Viewing Leases

### List Active Leases

```bash
akash query market lease list --owner $(akash keys show wallet -a) --state active
```

### Get Specific Lease

```bash
akash query market lease get \
  --owner $(akash keys show wallet -a) \
  --dseq <DSEQ> \
  --gseq 1 \
  --oseq 1 \
  --provider <PROVIDER>
```

### Get Lease Status (from Provider)

```bash
akash provider lease-status \
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
akash provider lease-status \
  --dseq <DSEQ> --gseq 1 --oseq 1 \
  --provider <PROVIDER> --from wallet | \
  jq '.services | to_entries[] | {name: .key, available: .value.available, total: .value.total}'
```

### View Logs

```bash
# All service logs
akash provider lease-logs \
  --dseq <DSEQ> --gseq 1 --oseq 1 \
  --provider <PROVIDER> --from wallet

# Specific service
akash provider lease-logs \
  --dseq <DSEQ> --gseq 1 --oseq 1 \
  --provider <PROVIDER> --from wallet \
  --service web

# Follow logs in real-time
akash provider lease-logs \
  --dseq <DSEQ> --gseq 1 --oseq 1 \
  --provider <PROVIDER> --from wallet \
  --follow --tail 100
```

### View Events

```bash
akash provider lease-events \
  --dseq <DSEQ> --gseq 1 --oseq 1 \
  --provider <PROVIDER> --from wallet
```

## Lease Operations

### Close Lease (Keep Deployment Open)

Close a single lease without closing the entire deployment:

```bash
akash tx market lease close \
  --dseq <DSEQ> \
  --gseq 1 \
  --oseq 1 \
  --from wallet
```

After closing, new bids will come in. Accept a new bid to create a fresh lease.

### Close Entire Deployment

Close deployment and all associated leases:

```bash
akash tx deployment close --dseq <DSEQ> --from wallet
```

### Migrate Provider

To move a deployment to a different provider:

```bash
# 1. Close current lease
akash tx market lease close \
  --dseq <DSEQ> --gseq 1 --oseq 1 --from wallet

# 2. Wait for new bids
sleep 30

# 3. List bids
akash query market bid list --owner $(akash keys show wallet -a) --dseq <DSEQ>

# 4. Accept new bid
akash tx market lease create \
  --dseq <DSEQ> --gseq 1 --oseq 2 \
  --provider <NEW_PROVIDER> --from wallet

# 5. Send manifest to new provider
akash provider send-manifest deploy.yaml \
  --dseq <DSEQ> --gseq 1 --oseq 2 \
  --provider <NEW_PROVIDER> --from wallet
```

Note: OSEQ increments when creating a new lease for the same group.

## Escrow Management

### Check Escrow Balance

```bash
akash query deployment get \
  --owner $(akash keys show wallet -a) \
  --dseq <DSEQ> | jq '.escrow_account'
```

### Deposit More Funds

```bash
akash tx deployment deposit 5000000uact --dseq <DSEQ> --from wallet
```

### Check Remaining Time

```bash
# Get current balance and price
BALANCE=$(akash query deployment get --owner $(akash keys show wallet -a) --dseq <DSEQ> -o json | jq -r '.escrow_account.balance.amount')
PRICE=$(akash query market lease get --owner $(akash keys show wallet -a) --dseq <DSEQ> --gseq 1 --oseq 1 --provider <PROVIDER> -o json | jq -r '.lease.price.amount')

echo "Blocks remaining: $(( $BALANCE / $PRICE ))"
echo "Hours remaining: $(( $BALANCE / $PRICE / 600 ))"
echo "Days remaining: $(( $BALANCE / $PRICE / 14400 ))"
```

## Interactive Shell

Access containers directly:

```bash
# Open shell
akash provider lease-shell \
  --dseq <DSEQ> --gseq 1 --oseq 1 \
  --provider <PROVIDER> --from wallet \
  --service web \
  -- /bin/sh

# Run specific command
akash provider lease-shell \
  --dseq <DSEQ> --gseq 1 --oseq 1 \
  --provider <PROVIDER> --from wallet \
  --service web \
  -- cat /etc/nginx/nginx.conf
```

## Troubleshooting

### Lease Not Active

```bash
# Check lease state
akash query market lease get --dseq <DSEQ> ... -o json | jq '.lease.state'
```

Possible states:
- `active` - Running normally
- `closed` - Terminated
- `insufficient_funds` - Escrow depleted

### Service Not Available

```bash
# Check events for errors
akash provider lease-events --dseq <DSEQ> ...

# Check logs for crash loops
akash provider lease-logs --dseq <DSEQ> ... --tail 50
```

### Cannot Send Manifest

- Verify certificate is active
- Check provider is online
- Wait and retry (provider may be processing)

### Escrow Depleted

```bash
# Deposit immediately
akash tx deployment deposit 10000000uact --dseq <DSEQ> --from wallet

# If deployment closed, create new one
akash tx deployment create deploy.yaml --from wallet
```

## Best Practices

1. **Monitor escrow** - Set up alerts before funds run out
2. **Use sufficient deposit** - Deposit at least 7 days worth
3. **Check logs regularly** - Catch issues early
4. **Keep SDL versioned** - Track changes to deployment config
5. **Test updates locally** - Validate SDL before updating
