# Kubernetes Cluster Setup for Akash Provider

Setting up a Kubernetes cluster to serve as the foundation for an Akash provider.

## Kubernetes Distribution Options

| Distribution | Best For | Complexity |
|--------------|----------|------------|
| k3s | Single-node, quick setup | Low |
| kubeadm | Multi-node, production | Medium |
| MicroK8s | Single-node, Ubuntu | Low |
| Managed (EKS/GKE/AKS) | Enterprise, multi-cloud | Medium |

## Option 1: k3s (Recommended for Single-Node)

### Install k3s

```bash
# Install k3s without Traefik (we use nginx-ingress instead)
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="--disable=traefik" sh -
```

### Verify Installation

```bash
# Check node status
sudo k3s kubectl get nodes

# Copy kubeconfig for kubectl access
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $(id -u):$(id -g) ~/.kube/config
export KUBECONFIG=~/.kube/config

# Verify kubectl works
kubectl get nodes
kubectl get pods -A
```

### k3s with Custom Options

```bash
# Multi-server setup (first server)
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="server \
  --disable=traefik \
  --cluster-init \
  --tls-san=provider.example.com" sh -

# Get join token
sudo cat /var/lib/rancher/k3s/server/node-token

# Additional server nodes
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="server \
  --disable=traefik" \
  K3S_URL=https://<FIRST_SERVER_IP>:6443 \
  K3S_TOKEN=<NODE_TOKEN> sh -

# Agent (worker) nodes
curl -sfL https://get.k3s.io | K3S_URL=https://<SERVER_IP>:6443 \
  K3S_TOKEN=<NODE_TOKEN> sh -
```

## Option 2: kubeadm (Production Multi-Node)

### Prerequisites

```bash
# Disable swap
sudo swapoff -a
sudo sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab

# Load kernel modules
cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF

sudo modprobe overlay
sudo modprobe br_netfilter

# Set sysctl params
cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF

sudo sysctl --system
```

### Install containerd

```bash
# Install containerd
sudo apt-get update
sudo apt-get install -y containerd

# Configure containerd
sudo mkdir -p /etc/containerd
containerd config default | sudo tee /etc/containerd/config.toml
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml
sudo systemctl restart containerd
```

### Install kubeadm, kubelet, kubectl

```bash
# Add Kubernetes repository
sudo apt-get install -y apt-transport-https ca-certificates curl gpg
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.29/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.29/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list

# Install
sudo apt-get update
sudo apt-get install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl
```

### Initialize Cluster

```bash
# Initialize control plane
sudo kubeadm init --pod-network-cidr=10.244.0.0/16

# Set up kubeconfig
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config

# Install CNI (Flannel)
kubectl apply -f https://github.com/flannel-io/flannel/releases/latest/download/kube-flannel.yml

# Allow scheduling on control plane (single-node only)
kubectl taint nodes --all node-role.kubernetes.io/control-plane-
```

### Join Worker Nodes

```bash
# On worker nodes, use the join command from kubeadm init output
sudo kubeadm join <CONTROL_PLANE_IP>:6443 --token <TOKEN> \
  --discovery-token-ca-cert-hash sha256:<HASH>

# If token expired, create a new one on the control plane
kubeadm token create --print-join-command
```

## NVIDIA GPU Support

Required for providers offering GPU compute.

### Step 1: Install NVIDIA Drivers

```bash
# Ubuntu
sudo apt-get update
sudo apt-get install -y linux-headers-$(uname -r)
sudo apt-get install -y nvidia-driver-535

# Verify driver installation
nvidia-smi
```

### Step 2: Install NVIDIA Container Toolkit

```bash
# Add NVIDIA Container Toolkit repository
distribution=$(. /etc/os-release;echo $ID$VERSION_ID) \
  && curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
  && curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# Install toolkit
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Configure containerd for NVIDIA
sudo nvidia-ctk runtime configure --runtime=containerd
sudo systemctl restart containerd
```

### Step 3: Install NVIDIA Device Plugin

```bash
# Deploy NVIDIA device plugin DaemonSet
kubectl create -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.3/nvidia-device-plugin.yml

# Verify GPU detection
kubectl get nodes -o json | jq '.items[].status.allocatable["nvidia.com/gpu"]'
```

### Step 4: Verify GPU Access

```bash
# Run a test pod with GPU
kubectl run gpu-test --image=nvidia/cuda:12.0-base-ubuntu22.04 \
  --restart=Never \
  --limits='nvidia.com/gpu=1' \
  -- nvidia-smi

# Check output
kubectl logs gpu-test

# Clean up
kubectl delete pod gpu-test
```

## Ingress Controller

The NGINX Ingress Controller is required for routing tenant HTTP/HTTPS traffic.

### Install via Helm

```bash
# Add Helm repo
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

# Install nginx-ingress
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.service.type=NodePort \
  --set controller.service.nodePorts.http=80 \
  --set controller.service.nodePorts.https=443 \
  --set controller.ingressClassResource.name=akash-ingress-class \
  --set controller.kind=DaemonSet \
  --set controller.hostPort.enabled=true
```

### Verify Ingress Controller

```bash
# Check ingress controller pods
kubectl get pods -n ingress-nginx

# Verify the controller is running
kubectl get svc -n ingress-nginx
```

## Persistent Volume Setup

### Local Path Provisioner (k3s Default)

k3s includes local-path-provisioner by default. Verify:

```bash
kubectl get storageclass
```

Expected output:
```
NAME                   PROVISIONER             RECLAIMPOLICY   VOLUMEBINDINGMODE
local-path (default)   rancher.io/local-path   Delete          WaitForFirstConsumer
```

### Custom Storage Classes for Akash

Create storage classes matching Akash conventions:

```yaml
# beta2-storage-class.yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: beta2
provisioner: rancher.io/local-path
reclaimPolicy: Delete
volumeBindingMode: WaitForFirstConsumer
parameters:
  nodePath: /var/lib/akash-storage/beta2
```

```bash
# Create the storage directory
sudo mkdir -p /var/lib/akash-storage/beta2

# Apply storage class
kubectl apply -f beta2-storage-class.yaml
```

### RAM Storage Class

```yaml
# ram-storage-class.yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ram
provisioner: rancher.io/local-path
reclaimPolicy: Delete
volumeBindingMode: WaitForFirstConsumer
parameters:
  nodePath: /dev/shm
```

```bash
kubectl apply -f ram-storage-class.yaml
```

### OpenEBS (Multi-Node Production)

```bash
# Install OpenEBS via Helm
helm repo add openebs https://openebs.github.io/charts
helm repo update

helm install openebs openebs/openebs \
  --namespace openebs \
  --create-namespace \
  --set localprovisioner.basePath=/var/openebs/local
```

## Node Labels

Label nodes with their capabilities for the Akash inventory operator:

```bash
# Label GPU nodes
kubectl label nodes <node-name> akash.network/capabilities.gpu.vendor.nvidia.model.a100=true

# Label storage nodes
kubectl label nodes <node-name> akash.network/capabilities.storage.class.beta2=true

# Label by region
kubectl label nodes <node-name> topology.kubernetes.io/region=us-west-2
```

## Cluster Verification

Run the following checks to verify the cluster is ready:

```bash
# All nodes Ready
kubectl get nodes
# Expected: All nodes in Ready state

# Core system pods running
kubectl get pods -n kube-system
# Expected: All pods Running or Completed

# Ingress controller running
kubectl get pods -n ingress-nginx
# Expected: Pods in Running state

# Storage classes available
kubectl get storageclass
# Expected: At least one storage class

# GPU available (if GPU provider)
kubectl describe nodes | grep -A 5 "nvidia.com/gpu"
# Expected: Shows GPU count in allocatable resources

# DNS resolution working
kubectl run dns-test --image=busybox:1.36 --restart=Never -- nslookup kubernetes.default
kubectl logs dns-test
kubectl delete pod dns-test
```

## Troubleshooting Cluster Setup

### Node Not Ready

```bash
# Check kubelet status
sudo systemctl status kubelet
sudo journalctl -u kubelet -f

# Check container runtime
sudo systemctl status containerd
```

### GPU Not Detected

```bash
# Verify NVIDIA driver
nvidia-smi

# Check device plugin pods
kubectl get pods -n kube-system -l app=nvidia-device-plugin-daemonset

# Check device plugin logs
kubectl logs -n kube-system -l app=nvidia-device-plugin-daemonset
```

### Pod Network Issues

```bash
# Check CNI plugin pods
kubectl get pods -n kube-system -l app=flannel

# Verify pod-to-pod connectivity
kubectl run test1 --image=busybox:1.36 --restart=Never -- sleep 3600
kubectl run test2 --image=busybox:1.36 --restart=Never -- sleep 3600
kubectl exec test1 -- ping -c 3 $(kubectl get pod test2 -o jsonpath='{.status.podIP}')
kubectl delete pod test1 test2
```

## Next Steps

- **@provider-installation.md** - Install Akash provider software
- **@configuration.md** - Configure provider settings
