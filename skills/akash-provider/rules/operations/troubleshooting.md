# Provider Troubleshooting

Common provider issues, diagnostic commands, and solutions.

## Diagnostic Checklist

When troubleshooting provider issues, check these in order:

```
1. Provider pod running?         kubectl get pods -n akash-services
2. Provider logs clean?          kubectl logs -n akash-services -l app=akash-provider --tail=50
3. Wallet has funds?             akash query bank balances <PROVIDER_ADDRESS>
4. Certificate valid?            akash query cert list --owner <PROVIDER_ADDRESS>
5. RPC node reachable?           curl -s <RPC_URL>/status
6. DNS resolving?                nslookup provider.example.com
7. Ports open?                   curl -sk https://provider.example.com:8443/status
8. Kubernetes healthy?           kubectl get nodes && kubectl get pods -A
9. Operators running?            kubectl get pods -n akash-services
10. Ingress controller running?  kubectl get pods -n ingress-nginx
```

## Provider Pod Issues

### Provider Pod Not Starting

**Symptoms:** Pod in CrashLoopBackOff or Error state.

```bash
# Check pod status
kubectl get pods -n akash-services -l app=akash-provider

# View pod events
kubectl describe pod -n akash-services -l app=akash-provider

# Check logs for errors
kubectl logs -n akash-services -l app=akash-provider --previous
```

**Common causes and fixes:**

| Cause | Fix |
|-------|-----|
| Invalid wallet key | Recreate the Kubernetes secret with correct key |
| Wrong chain ID | Update `chainid` in Helm values |
| RPC node unreachable | Verify RPC endpoint and network connectivity |
| Invalid certificate | Regenerate provider certificate |
| Port conflict | Check no other service uses port 8443 |

### Provider Pod Running but Not Bidding

**Symptoms:** Pod shows Running status but no bids are submitted.

```bash
# Check provider logs for order processing
kubectl logs -n akash-services -l app=akash-provider --tail=200 | grep -i "order\|bid\|skip"

# Verify provider is registered
akash query provider get <PROVIDER_ADDRESS> \
  --node https://rpc.akashnet.net:443

# Check if provider is in the active set
akash query provider list \
  --node https://rpc.akashnet.net:443 \
  --output json | jq '.providers[] | select(.owner == "<PROVIDER_ADDRESS>")'
```

**Common causes and fixes:**

| Cause | Fix |
|-------|-----|
| No matching orders | Verify attributes match common SDL requirements |
| Insufficient resources | Free up cluster resources or increase capacity |
| Pricing too high | Lower prices in bid pricing script |
| Missing auditor signature | Get attributes signed by an auditor |
| Wallet out of gas | Add AKT to provider wallet |

## Pod Scheduling Failures

### Insufficient CPU or Memory

**Symptoms:** Tenant pods stuck in Pending state.

```bash
# Check pod events
kubectl describe pod <POD_NAME> -n <LEASE_NAMESPACE>
# Look for: "Insufficient cpu" or "Insufficient memory"

# Check node allocatable resources
kubectl describe nodes | grep -A 10 "Allocated resources"

# Check resource requests vs available
kubectl top nodes
```

**Fixes:**

```bash
# Option 1: Add more nodes to the cluster
# Option 2: Reduce overcommit settings
# Option 3: Close underperforming leases to free resources

# Verify inventory operator is reporting correctly
kubectl logs -n akash-services -l app=inventory-operator --tail=50
```

### Insufficient GPU

**Symptoms:** GPU workload pods stuck in Pending.

```bash
# Check GPU availability
kubectl describe nodes | grep -A 5 "nvidia.com/gpu"

# Check which pods are consuming GPUs
kubectl get pods --all-namespaces -o json | \
  jq -r '.items[] | select(.spec.containers[].resources.limits."nvidia.com/gpu" != null) |
  "\(.metadata.namespace)/\(.metadata.name): \(.spec.containers[0].resources.limits."nvidia.com/gpu") GPU(s)"'

# Verify NVIDIA device plugin is running
kubectl get pods -n kube-system -l app=nvidia-device-plugin-daemonset
```

**Fixes:**

| Issue | Solution |
|-------|----------|
| All GPUs allocated | Wait for existing GPU leases to close |
| Device plugin not running | Restart nvidia-device-plugin DaemonSet |
| Driver mismatch | Update NVIDIA drivers to match CUDA requirements |
| GPU not detected | Check `nvidia-smi` on host, reinstall drivers |

### Storage Issues

**Symptoms:** Pods fail to mount volumes, PVC stuck in Pending.

```bash
# Check PVC status
kubectl get pvc -n <LEASE_NAMESPACE>

# Describe PVC for events
kubectl describe pvc <PVC_NAME> -n <LEASE_NAMESPACE>

# Check storage class exists
kubectl get storageclass

# Check available disk space
df -h /var/lib/akash-storage/
```

**Fixes:**

| Issue | Solution |
|-------|----------|
| StorageClass not found | Create the missing storage class (beta2, beta3, ram) |
| Insufficient disk space | Free disk space or add storage |
| Volume provisioner down | Restart local-path-provisioner or OpenEBS |
| PVC stuck in Pending | Check provisioner logs for errors |

## Networking Issues

### Tenant Services Not Accessible

**Symptoms:** Deployment is running but services return 502/503 or timeout.

```bash
# Check ingress controller is running
kubectl get pods -n ingress-nginx

# Check ingress rules for the lease
kubectl get ingress -n <LEASE_NAMESPACE>
kubectl describe ingress -n <LEASE_NAMESPACE>

# Check if the service has endpoints
kubectl get endpoints -n <LEASE_NAMESPACE>

# Test connectivity from inside the cluster
kubectl run test-curl --image=curlimages/curl --restart=Never -- \
  curl -v http://<SERVICE_NAME>.<LEASE_NAMESPACE>.svc.cluster.local
kubectl logs test-curl
kubectl delete pod test-curl
```

**Fixes:**

| Issue | Solution |
|-------|----------|
| Ingress controller down | Restart nginx-ingress pods |
| No endpoints | Check pod readiness probes, ensure pods are Running |
| DNS wildcard not set | Configure `*.ingress.example.com` DNS record |
| Port mismatch | Verify service port matches container expose port |

### Hostname Operator Issues

**Symptoms:** Tenant hostnames not being created or routed.

```bash
# Check hostname operator logs
kubectl logs -n akash-services -l app=hostname-operator -f

# Check managed hostnames
kubectl get providerhost --all-namespaces

# Restart hostname operator
kubectl rollout restart deployment hostname-operator -n akash-services
```

### Provider API Not Accessible

**Symptoms:** Cannot reach provider at `https://provider.example.com:8443`.

```bash
# Check provider service
kubectl get svc -n akash-services

# Test from inside the cluster
kubectl run test-curl --image=curlimages/curl --restart=Never -- \
  curl -sk https://akash-provider.akash-services.svc.cluster.local:8443/status
kubectl logs test-curl
kubectl delete pod test-curl

# Check firewall rules
sudo ufw status
# Ensure port 8443 is allowed

# Verify DNS
nslookup provider.example.com
# Should resolve to provider's public IP

# Check TLS certificate
openssl s_client -connect provider.example.com:8443 </dev/null 2>/dev/null | \
  openssl x509 -noout -dates
```

## Certificate Issues

### Provider Certificate Expired

**Symptoms:** Tenants cannot send manifests or communicate with provider.

```bash
# Check certificate status
akash query cert list --owner <PROVIDER_ADDRESS> \
  --node https://rpc.akashnet.net:443

# Regenerate certificate
akash tx cert revoke --from provider-wallet \
  --chain-id akashnet-2 \
  --node https://rpc.akashnet.net:443

akash tx cert create server provider.example.com \
  --from provider-wallet \
  --chain-id akashnet-2 \
  --node https://rpc.akashnet.net:443

# Restart provider to pick up new certificate
kubectl rollout restart deployment akash-provider -n akash-services
```

### Certificate Mismatch

**Symptoms:** mTLS handshake failures in provider logs.

```bash
# Verify the provider hostname matches the certificate
# The certificate must match the hostname in provider registration

# Check registered hostname
akash query provider get <PROVIDER_ADDRESS> \
  --node https://rpc.akashnet.net:443 \
  --output json | jq -r '.provider.host_uri'

# Certificate should be created for this hostname
# If different, recreate the certificate with the correct hostname
```

## Bid Failures

### Bids Not Being Submitted

```bash
# Check provider logs for bid-related messages
kubectl logs -n akash-services -l app=akash-provider --tail=200 | grep -iE "bid|order|skip|reject"

# Check wallet balance (need gas for bid transactions)
akash query bank balances <PROVIDER_ADDRESS> \
  --node https://rpc.akashnet.net:443

# Check if pricing script has errors
kubectl logs -n akash-services -l app=akash-provider | grep -i "price\|script\|error"
```

**Common bid failure causes:**

| Cause | Diagnostic | Fix |
|-------|------------|-----|
| Out of gas | Balance query shows < 0.1 AKT | Fund wallet |
| Pricing script error | Error messages in logs | Fix script syntax |
| Resource mismatch | "skipping order" in logs | Update attributes or capacity |
| Auditor missing | "no matching auditor" in logs | Get attributes signed |
| RPC timeout | Connection errors in logs | Switch RPC endpoint |

### Bids Submitted but Never Accepted

This is typically a pricing issue, not a technical problem:

```bash
# Compare your bid prices with winning bids
akash query market lease list \
  --state active \
  --node https://rpc.akashnet.net:443 \
  --output json | jq '.leases[].lease.price'

# Check market competition
akash query provider list \
  --node https://rpc.akashnet.net:443 \
  --output json | jq '.providers | length'
```

**Fixes:**

- Lower bid prices in pricing script
- Ensure attributes match common SDL requirements
- Verify provider uptime and reliability

## Inventory Operator Issues

### Resources Not Reported Correctly

```bash
# Check inventory operator logs
kubectl logs -n akash-services -l app=inventory-operator --tail=100

# Verify reported inventory
kubectl logs -n akash-services -l app=inventory-operator | grep -i "inventory\|resource\|capacity"

# Restart inventory operator
kubectl rollout restart deployment inventory-operator -n akash-services
```

### GPU Not Reported in Inventory

```bash
# Verify GPU is visible to Kubernetes
kubectl describe nodes | grep -A 5 "nvidia.com/gpu"

# Check device plugin
kubectl get pods -n kube-system | grep nvidia
kubectl logs -n kube-system -l app=nvidia-device-plugin-daemonset

# Restart device plugin
kubectl rollout restart daemonset nvidia-device-plugin -n kube-system

# Then restart inventory operator
kubectl rollout restart deployment inventory-operator -n akash-services
```

## Performance Issues

### High Provider Latency

```bash
# Check RPC response time
time curl -s https://rpc.akashnet.net:443/status

# Check provider pod resource usage
kubectl top pods -n akash-services

# If provider pod is resource-constrained, increase limits
# In provider-values.yaml:
# resources:
#   limits:
#     cpu: 4
#     memory: 4Gi
```

### Slow Lease Deployment

```bash
# Check image pull times
kubectl get events -n <LEASE_NAMESPACE> --sort-by='.lastTimestamp' | grep -i pull

# Check node disk I/O
iostat -x 1 5

# Check container runtime performance
kubectl get pods --all-namespaces | wc -l
# If too many pods, cluster may be overloaded
```

## Recovery Procedures

### Full Provider Restart

```bash
# Restart all provider components
kubectl rollout restart deployment akash-provider -n akash-services
kubectl rollout restart deployment hostname-operator -n akash-services
kubectl rollout restart deployment inventory-operator -n akash-services

# Wait for pods to restart
kubectl get pods -n akash-services -w
```

### Clean Slate Recovery

If the provider is in a bad state and needs complete reset:

```bash
# 1. Close all active leases on chain (careful - this disrupts tenants)
# Only if absolutely necessary

# 2. Uninstall provider charts
helm uninstall akash-provider -n akash-services
helm uninstall hostname-operator -n akash-services
helm uninstall inventory-operator -n akash-services

# 3. Clean up lease namespaces
kubectl get ns -l akash.network=true -o name | xargs kubectl delete

# 4. Reinstall provider
helm install akash-provider akash/provider \
  --namespace akash-services \
  --values provider-values.yaml
helm install hostname-operator akash/hostname-operator \
  --namespace akash-services
helm install inventory-operator akash/inventory-operator \
  --namespace akash-services
```

## Diagnostic Commands Quick Reference

| Diagnostic | Command |
|-----------|---------|
| Provider status | `kubectl get pods -n akash-services` |
| Provider logs | `kubectl logs -n akash-services -l app=akash-provider --tail=100` |
| Provider errors | `kubectl logs -n akash-services -l app=akash-provider \| grep -i error` |
| Node health | `kubectl get nodes -o wide` |
| Resource usage | `kubectl top nodes` |
| All tenant pods | `kubectl get pods --all-namespaces -l akash.network=true` |
| Lease namespaces | `kubectl get ns -l akash.network=true` |
| Pod events | `kubectl get events -n <NS> --sort-by='.lastTimestamp'` |
| Wallet balance | `akash query bank balances <ADDR>` |
| Certificate check | `akash query cert list --owner <ADDR>` |
| Provider registration | `akash query provider get <ADDR>` |
| Active leases | `akash query market lease list --provider <ADDR> --state active` |
| Open bids | `akash query market bid list --provider <ADDR> --state open` |
| GPU status | `kubectl describe nodes \| grep -A 5 "nvidia.com/gpu"` |
| Ingress controller | `kubectl get pods -n ingress-nginx` |
| DNS test | `nslookup provider.example.com` |
| Port test | `curl -sk https://provider.example.com:8443/status` |

## Getting Help

| Resource | Link |
|----------|------|
| Akash Discord | #providers channel |
| Akash Documentation | https://docs.akash.network |
| GitHub Issues | https://github.com/akash-network/provider/issues |
| Provider Community | Akash Providers SIG |
