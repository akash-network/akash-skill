# Lease Management

Managing active leases, handling lifecycle events, troubleshooting stuck leases, and configuring eviction policies.

## Lease Lifecycle

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Order   │────►│   Bid    │────►│  Lease   │────►│  Closed  │
│  Created │     │ Accepted │     │  Active  │     │          │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
                                       │
                                       │ Triggers:
                                       │ - Tenant closes deployment
                                       │ - Escrow depleted
                                       │ - Provider eviction
                                       │ - Lease timeout
                                       │
                                       ▼
                                  ┌──────────┐
                                  │ Resources │
                                  │ Reclaimed │
                                  └──────────┘
```

## Viewing Active Leases

### List All Active Leases

```bash
# Via Akash CLI
akash query market lease list \
  --provider <PROVIDER_ADDRESS> \
  --state active \
  --node https://rpc.akashnet.net:443 \
  --output json
```

### Detailed Lease Information

```bash
# Get specific lease details
akash query market lease get \
  --owner <TENANT_ADDRESS> \
  --dseq <DSEQ> \
  --gseq 1 \
  --oseq 1 \
  --provider <PROVIDER_ADDRESS> \
  --node https://rpc.akashnet.net:443 \
  --output json
```

### Lease Output Fields

| Field | Description |
|-------|-------------|
| `lease_id.owner` | Tenant's Akash address |
| `lease_id.dseq` | Deployment sequence number |
| `lease_id.gseq` | Group sequence number |
| `lease_id.oseq` | Order sequence number |
| `lease_id.provider` | Provider's Akash address |
| `price.denom` | Payment denomination (uact) |
| `price.amount` | Price per block |
| `state` | Lease state (active, closed, etc.) |

## Kubernetes Resources per Lease

Each active lease maps to Kubernetes resources:

```bash
# List namespaces for active leases
kubectl get namespaces -l akash.network=true

# Get all resources in a lease namespace
kubectl get all -n <LEASE_NAMESPACE>

# Lease namespace format: <truncated-owner-hash>-<dseq>
```

### Checking Lease Pods

```bash
# List pods for a specific lease
kubectl get pods -n <LEASE_NAMESPACE> -o wide

# Describe a pod for details
kubectl describe pod <POD_NAME> -n <LEASE_NAMESPACE>

# Get pod logs
kubectl logs <POD_NAME> -n <LEASE_NAMESPACE>
kubectl logs <POD_NAME> -n <LEASE_NAMESPACE> --previous  # Previous container logs
```

### Checking Lease Services

```bash
# List services
kubectl get svc -n <LEASE_NAMESPACE>

# Check ingress routes
kubectl get ingress -n <LEASE_NAMESPACE>

# Describe ingress for troubleshooting
kubectl describe ingress -n <LEASE_NAMESPACE>
```

### Checking Lease Storage

```bash
# Persistent volume claims for a lease
kubectl get pvc -n <LEASE_NAMESPACE>

# Persistent volume details
kubectl describe pvc <PVC_NAME> -n <LEASE_NAMESPACE>
```

## Troubleshooting Stuck Leases

### Lease Active but Pods Not Running

```bash
# Check pod status and events
kubectl get pods -n <LEASE_NAMESPACE>
kubectl describe pods -n <LEASE_NAMESPACE>

# Common causes:
# - ImagePullBackOff: Container image not found or auth required
# - Pending: Insufficient resources or scheduling constraints
# - CrashLoopBackOff: Application crashing on startup
# - ContainerCreating: Volume mount or network issues
```

### Pods Stuck in Pending State

```bash
# Check events for scheduling issues
kubectl get events -n <LEASE_NAMESPACE> --sort-by='.lastTimestamp'

# Check node capacity
kubectl describe nodes | grep -A 10 "Allocated resources"

# Check if resource requests exceed available capacity
kubectl get pod <POD_NAME> -n <LEASE_NAMESPACE> -o json | \
  jq '.spec.containers[].resources'
```

### Pods Stuck in ImagePullBackOff

```bash
# Check pod events for image pull errors
kubectl describe pod <POD_NAME> -n <LEASE_NAMESPACE> | grep -A 10 Events

# Verify image exists
# The tenant may have specified a non-existent or private image
```

### Lease Namespace Stuck After Closure

```bash
# Check for finalizers preventing deletion
kubectl get namespace <LEASE_NAMESPACE> -o json | jq '.spec.finalizers'

# If namespace is stuck in Terminating state
kubectl get pods -n <LEASE_NAMESPACE>
# Force delete any stuck pods
kubectl delete pods --all -n <LEASE_NAMESPACE> --grace-period=0 --force
```

## Lease Withdrawal

### Automatic Withdrawal

The provider automatically withdraws earned funds based on the `withdrawalperiod` setting:

```yaml
# provider-values.yaml
withdrawalperiod: 720  # Every ~72 minutes
```

### Manual Withdrawal

```bash
# Manually trigger withdrawal for all leases
akash tx market lease withdraw \
  --dseq <DSEQ> \
  --gseq 1 \
  --oseq 1 \
  --from provider-wallet \
  --chain-id akashnet-2 \
  --node https://rpc.akashnet.net:443
```

### Check Withdrawal History

```bash
# Query transactions for withdrawal events
akash query txs --events 'message.action=/akash.market.v1beta4.MsgWithdrawLease' \
  --events "message.sender=<PROVIDER_ADDRESS>" \
  --node https://rpc.akashnet.net:443
```

## Eviction Policies

Providers can evict tenants under certain conditions.

### Reasons for Eviction

| Reason | Description |
|--------|-------------|
| Escrow Depleted | Tenant's deployment escrow runs out of funds |
| Resource Abuse | Tenant exceeds allocated resource limits |
| Policy Violation | Tenant runs prohibited content or services |
| Maintenance | Provider needs to take infrastructure offline |

### Closing a Lease (Provider-Side)

```bash
# Close a specific lease
akash tx market lease close \
  --dseq <DSEQ> \
  --gseq 1 \
  --oseq 1 \
  --from provider-wallet \
  --chain-id akashnet-2 \
  --node https://rpc.akashnet.net:443
```

### Escrow Depletion Handling

When a tenant's escrow is depleted:

1. The blockchain automatically marks the lease as insufficient funds
2. The provider detects the state change
3. The provider's lease manager cleans up Kubernetes resources
4. The namespace and all resources are deleted

```bash
# Check leases with insufficient funds
akash query market lease list \
  --provider <PROVIDER_ADDRESS> \
  --state insufficient-funds \
  --node https://rpc.akashnet.net:443
```

## Resource Reclamation

When a lease is closed, resources are reclaimed:

### Automatic Cleanup

The provider automatically:

1. Terminates all pods in the lease namespace
2. Deletes services and ingress rules
3. Removes persistent volume claims (data is deleted)
4. Deletes the Kubernetes namespace
5. Updates available inventory

### Verify Cleanup

```bash
# Check that the namespace is removed
kubectl get namespace <LEASE_NAMESPACE>
# Should return "not found" after cleanup

# Verify resources are freed
kubectl top nodes
kubectl describe nodes | grep -A 10 "Allocated resources"

# Check persistent volumes are released
kubectl get pv | grep Released
```

### Manual Cleanup (If Needed)

```bash
# If a lease namespace is stuck after closure
kubectl get pods -n <LEASE_NAMESPACE>

# Force delete all resources
kubectl delete all --all -n <LEASE_NAMESPACE>
kubectl delete pvc --all -n <LEASE_NAMESPACE>

# Delete the namespace
kubectl delete namespace <LEASE_NAMESPACE>

# If namespace is stuck in Terminating, remove finalizers
kubectl get namespace <LEASE_NAMESPACE> -o json | \
  jq '.spec.finalizers = []' | \
  kubectl replace --raw "/api/v1/namespaces/<LEASE_NAMESPACE>/finalize" -f -
```

## Lease Summary Commands

| Task | Command |
|------|---------|
| List active leases | `akash query market lease list --provider <ADDR> --state active` |
| Lease details | `akash query market lease get --owner <OWNER> --dseq <DSEQ> --gseq 1 --oseq 1 --provider <ADDR>` |
| Lease pods | `kubectl get pods -n <LEASE_NS>` |
| Lease events | `kubectl get events -n <LEASE_NS> --sort-by='.lastTimestamp'` |
| Lease logs | `kubectl logs <POD> -n <LEASE_NS>` |
| Close lease | `akash tx market lease close --dseq <DSEQ> --gseq 1 --oseq 1 --from provider-wallet` |
| Withdraw funds | `akash tx market lease withdraw --dseq <DSEQ> --gseq 1 --oseq 1 --from provider-wallet` |
| All lease namespaces | `kubectl get ns -l akash.network=true` |
| Lease resource usage | `kubectl top pods -n <LEASE_NS>` |

## Best Practices

| Practice | Recommendation |
|----------|---------------|
| Monitoring | Regularly check for stuck or failing leases |
| Withdrawal | Set withdrawal period based on gas cost tradeoff |
| Cleanup | Monitor for orphaned namespaces or resources |
| Capacity | Keep 10-20% resource headroom for new deployments |
| Logging | Retain provider logs for at least 7 days |
| Alerts | Set up alerts for lease count drops or stuck states |

## Next Steps

- **@monitoring.md** - Set up comprehensive monitoring
- **@troubleshooting.md** - Diagnose common provider issues
