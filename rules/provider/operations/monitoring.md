# Provider Monitoring

Monitoring provider health, resource utilization, lease status, and performance metrics.

## Provider Status Overview

### Quick Health Check

```bash
# Check all provider pods are running
kubectl get pods -n akash-services

# Expected output:
# NAME                                   READY   STATUS    RESTARTS
# akash-provider-xxx                     1/1     Running   0
# hostname-operator-xxx                  1/1     Running   0
# inventory-operator-xxx                 1/1     Running   0
```

### Provider API Status

```bash
# Check provider status endpoint
curl -sk https://provider.example.com:8443/status

# Check provider version
curl -sk https://provider.example.com:8443/version
```

### On-Chain Provider Status

```bash
# Verify provider registration
akash query provider get <PROVIDER_ADDRESS> \
  --node https://rpc.akashnet.net:443 \
  --output json

# Check provider's active leases
akash query market lease list \
  --provider <PROVIDER_ADDRESS> \
  --state active \
  --node https://rpc.akashnet.net:443 \
  --output json | jq '.leases | length'

# Check provider's open bids
akash query market bid list \
  --provider <PROVIDER_ADDRESS> \
  --state open \
  --node https://rpc.akashnet.net:443 \
  --output json | jq '.bids | length'
```

## Resource Utilization Monitoring

### Cluster Resource Usage

```bash
# Node resource summary
kubectl top nodes

# Example output:
# NAME       CPU(cores)   CPU%   MEMORY(bytes)   MEMORY%
# node-1     12500m       39%    98304Mi          76%

# Pod resource usage
kubectl top pods --all-namespaces --sort-by=memory

# Resource allocation summary
kubectl describe nodes | grep -A 10 "Allocated resources"
```

### GPU Monitoring

```bash
# Check GPU allocation
kubectl describe nodes | grep -A 5 "nvidia.com/gpu"

# Check which pods are using GPUs
kubectl get pods --all-namespaces -o json | \
  jq '.items[] | select(.spec.containers[].resources.limits."nvidia.com/gpu" != null) |
  {namespace: .metadata.namespace, name: .metadata.name,
   gpu: .spec.containers[0].resources.limits."nvidia.com/gpu"}'

# Run nvidia-smi on GPU nodes (if accessible)
kubectl run gpu-check --image=nvidia/cuda:12.0-base-ubuntu22.04 \
  --restart=Never --limits='nvidia.com/gpu=1' -- nvidia-smi
kubectl logs gpu-check
kubectl delete pod gpu-check
```

### Storage Monitoring

```bash
# Check persistent volume claims
kubectl get pvc --all-namespaces

# Check persistent volumes
kubectl get pv

# Storage capacity by node
kubectl get nodes -o json | jq '.items[] |
  {name: .metadata.name,
   storage: .status.allocatable."ephemeral-storage"}'

# Disk usage on provider node
df -h /var/lib/akash-storage/
```

## Lease Monitoring

### Active Lease Summary

```bash
# Count active leases
akash query market lease list \
  --provider <PROVIDER_ADDRESS> \
  --state active \
  --node https://rpc.akashnet.net:443 \
  --output json | jq '.leases | length'

# List active leases with prices
akash query market lease list \
  --provider <PROVIDER_ADDRESS> \
  --state active \
  --node https://rpc.akashnet.net:443 \
  --output json | jq '.leases[] | {
    owner: .lease.lease_id.owner,
    dseq: .lease.lease_id.dseq,
    price: .lease.price
  }'
```

### Per-Lease Health

```bash
# Check pods for a specific lease namespace
# Lease namespaces follow the format: <owner-hash>-<dseq>
kubectl get pods -n <LEASE_NAMESPACE>

# Check events in lease namespace
kubectl get events -n <LEASE_NAMESPACE> --sort-by='.lastTimestamp'

# Check services in lease namespace
kubectl get svc -n <LEASE_NAMESPACE>

# Check ingress in lease namespace
kubectl get ingress -n <LEASE_NAMESPACE>
```

### Revenue Monitoring

```bash
# Check provider wallet balance
akash query bank balances <PROVIDER_ADDRESS> \
  --node https://rpc.akashnet.net:443

# Calculate total revenue per block from active leases
akash query market lease list \
  --provider <PROVIDER_ADDRESS> \
  --state active \
  --node https://rpc.akashnet.net:443 \
  --output json | jq '[.leases[].lease.price.amount | tonumber] | add'

# Estimate monthly revenue
# monthly_uact = total_per_block * 438000
```

## Provider Logs

### Core Provider Logs

```bash
# Follow provider logs
kubectl logs -n akash-services -l app=akash-provider -f

# Last 100 lines
kubectl logs -n akash-services -l app=akash-provider --tail=100

# Filter for errors
kubectl logs -n akash-services -l app=akash-provider | grep -i error

# Filter for bid activity
kubectl logs -n akash-services -l app=akash-provider | grep -i "bid"

# Filter for lease activity
kubectl logs -n akash-services -l app=akash-provider | grep -i "lease"
```

### Operator Logs

```bash
# Hostname operator logs
kubectl logs -n akash-services -l app=hostname-operator -f

# Inventory operator logs
kubectl logs -n akash-services -l app=inventory-operator -f

# IP operator logs (if installed)
kubectl logs -n akash-services -l app=ip-operator -f
```

## Prometheus Metrics

### Enabling Prometheus Metrics

Configure the provider to expose Prometheus metrics:

```yaml
# provider-values.yaml
metrics:
  enabled: true
  port: 9090
```

### Key Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `akash_provider_active_leases` | Gauge | Number of active leases |
| `akash_provider_available_cpu` | Gauge | Available CPU (millicpu) |
| `akash_provider_available_memory` | Gauge | Available memory (bytes) |
| `akash_provider_available_storage` | Gauge | Available storage (bytes) |
| `akash_provider_available_gpu` | Gauge | Available GPU count |
| `akash_provider_bids_submitted` | Counter | Total bids submitted |
| `akash_provider_bids_won` | Counter | Total bids accepted |
| `akash_provider_revenue_uakt` | Counter | Total revenue earned (uakt) |
| `akash_provider_orders_received` | Counter | Total orders seen |
| `akash_provider_orders_skipped` | Counter | Orders skipped (no match) |

### Prometheus ServiceMonitor

```yaml
# servicemonitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: akash-provider
  namespace: akash-services
spec:
  selector:
    matchLabels:
      app: akash-provider
  endpoints:
    - port: metrics
      interval: 30s
      path: /metrics
```

```bash
kubectl apply -f servicemonitor.yaml
```

## Grafana Dashboards

### Provider Overview Dashboard

Key panels for a provider dashboard:

| Panel | Visualization | Query |
|-------|---------------|-------|
| Active Leases | Stat | `akash_provider_active_leases` |
| CPU Utilization | Gauge | `1 - (akash_provider_available_cpu / akash_provider_total_cpu)` |
| Memory Utilization | Gauge | `1 - (akash_provider_available_memory / akash_provider_total_memory)` |
| GPU Utilization | Gauge | `1 - (akash_provider_available_gpu / akash_provider_total_gpu)` |
| Bids Submitted (24h) | Stat | `increase(akash_provider_bids_submitted[24h])` |
| Bid Win Rate | Stat | `increase(akash_provider_bids_won[24h]) / increase(akash_provider_bids_submitted[24h])` |
| Revenue (24h) | Stat | `increase(akash_provider_revenue_uakt[24h])` |
| Leases Over Time | Time Series | `akash_provider_active_leases` |

### Kubernetes Cluster Dashboard

Standard Kubernetes metrics to monitor alongside Akash:

| Panel | Description |
|-------|-------------|
| Node CPU Usage | CPU utilization per node |
| Node Memory Usage | Memory utilization per node |
| Pod Count | Total pods vs capacity |
| Network I/O | Network throughput per node |
| Disk I/O | Storage throughput per node |
| Pod Restart Count | Detect unstable tenant workloads |

## Alerting

### Recommended Alerts

| Alert | Condition | Severity |
|-------|-----------|----------|
| Provider Pod Down | Provider pod not running for > 5 min | Critical |
| High CPU Usage | Cluster CPU > 90% for > 15 min | Warning |
| High Memory Usage | Cluster memory > 90% for > 15 min | Warning |
| GPU Fully Allocated | No GPUs available for > 1 hour | Info |
| Low Wallet Balance | Provider wallet < 1 AKT | Critical |
| No Bids in 1 Hour | Zero bids submitted in last hour | Warning |
| Hostname Operator Down | Hostname operator not running | Critical |
| Inventory Operator Down | Inventory operator not running | Critical |
| Certificate Expiring | Provider cert expires in < 7 days | Warning |

### Example AlertManager Rule

```yaml
# alerting-rules.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: akash-provider-alerts
  namespace: akash-services
spec:
  groups:
    - name: akash-provider
      rules:
        - alert: AkashProviderDown
          expr: up{job="akash-provider"} == 0
          for: 5m
          labels:
            severity: critical
          annotations:
            summary: "Akash provider is down"
            description: "The Akash provider pod has been down for more than 5 minutes."

        - alert: HighClusterCPU
          expr: (1 - akash_provider_available_cpu / akash_provider_total_cpu) > 0.9
          for: 15m
          labels:
            severity: warning
          annotations:
            summary: "Cluster CPU usage above 90%"

        - alert: LowWalletBalance
          expr: akash_provider_wallet_balance_uakt < 1000000
          for: 5m
          labels:
            severity: critical
          annotations:
            summary: "Provider wallet balance below 1 AKT"
```

## Monitoring Commands Quick Reference

| Task | Command |
|------|---------|
| Provider pods status | `kubectl get pods -n akash-services` |
| Provider logs | `kubectl logs -n akash-services -l app=akash-provider -f` |
| Node resources | `kubectl top nodes` |
| Active leases count | `akash query market lease list --provider <ADDR> --state active -o json \| jq '.leases \| length'` |
| Wallet balance | `akash query bank balances <ADDR>` |
| All tenant pods | `kubectl get pods --all-namespaces -l akash.network=true` |
| Events (recent) | `kubectl get events --all-namespaces --sort-by='.lastTimestamp' --field-selector type=Warning` |
| GPU status | `kubectl describe nodes \| grep -A 5 "nvidia.com/gpu"` |
| Storage usage | `kubectl get pv,pvc --all-namespaces` |
| Ingress status | `kubectl get ingress --all-namespaces` |

## Next Steps

- **@lease-management.md** - Manage active leases
- **@troubleshooting.md** - Diagnose and fix issues
