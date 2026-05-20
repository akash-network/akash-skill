# Full Node Requirements

## Hardware Requirements

Running an Akash full node requires adequate hardware to keep up with block production, store chain state, and handle RPC queries.

### Minimum Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 4 cores | 8+ cores |
| RAM | 16 GB | 32 GB |
| Storage | 500 GB SSD | 1 TB NVMe SSD |
| Network | 100 Mbps | 1 Gbps |
| I/O | Standard SSD | NVMe SSD (high IOPS) |

### Storage Considerations

| Configuration | Storage Needs | Notes |
|---------------|---------------|-------|
| Pruned node | 200-500 GB | Default pruning keeps recent state only |
| Archive node | 2+ TB (growing) | Stores all historical states |
| State sync bootstrap | Minimal initially | Starts from recent snapshot |
| Snapshot bootstrap | 200-400 GB initially | Downloads compressed state |

**Important:** Storage requirements grow over time as the chain produces more blocks. Plan for growth and monitor disk usage regularly.

### Pruning Strategies

| Strategy | Description | Storage Impact |
|----------|-------------|----------------|
| `default` | Keeps last 100 states + every 500th state | Moderate |
| `nothing` | Archive node, keeps everything | Very high |
| `everything` | Aggressive pruning, keeps only current state | Low |
| `custom` | User-defined keep-recent, interval, and keep-every | Variable |

Example pruning configuration in `app.toml`:

```toml
# Pruning strategy
pruning = "custom"

# Number of recent states to keep
pruning-keep-recent = "100"

# Interval between pruned states
pruning-interval = "10"

# Keep every Nth state (0 to disable)
pruning-keep-every = "0"
```

## Software Requirements

### Operating System

| OS | Support Level | Notes |
|----|---------------|-------|
| Ubuntu 22.04 LTS | Recommended | Most tested and documented |
| Ubuntu 24.04 LTS | Supported | Works well |
| Debian 12 | Supported | Stable alternative |
| CentOS/RHEL 8+ | Supported | Enterprise environments |
| macOS | Development only | Not recommended for production |
| Windows | Not supported | Use WSL2 if necessary |

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| Go | 1.21+ | Required if building from source |
| make | Any | Build tooling |
| git | Any | Cloning repositories |
| curl / wget | Any | Downloading files |
| jq | Any | JSON processing for scripts |
| lz4 | Any | Snapshot decompression |

### Installing Dependencies (Ubuntu 22.04)

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y \
  build-essential \
  git \
  curl \
  wget \
  jq \
  lz4 \
  unzip \
  make \
  gcc

# Install Go (check for latest version)
GO_VERSION="1.22.5"
wget "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz"
sudo rm -rf /usr/local/go
sudo tar -C /usr/local -xzf "go${GO_VERSION}.linux-amd64.tar.gz"
rm "go${GO_VERSION}.linux-amd64.tar.gz"

# Add Go to PATH (add to ~/.bashrc or ~/.profile for persistence)
export GOROOT=/usr/local/go
export GOPATH=$HOME/go
export PATH=$PATH:$GOROOT/bin:$GOPATH/bin
```

## Network Requirements

### Ports

The following ports must be accessible for a full node:

| Port | Protocol | Direction | Purpose | Required |
|------|----------|-----------|---------|----------|
| 26656 | TCP | Inbound/Outbound | P2P networking | Yes |
| 26657 | TCP | Inbound | Tendermint RPC | Optional (if serving RPC) |
| 26660 | TCP | Inbound | Prometheus metrics | Optional |
| 1317 | TCP | Inbound | REST API (LCD) | Optional |
| 9090 | TCP | Inbound | gRPC | Optional |
| 9091 | TCP | Inbound | gRPC-web | Optional |

### Firewall Configuration (UFW)

```bash
# Allow SSH (adjust if using non-default port)
sudo ufw allow 22/tcp

# Allow P2P (required)
sudo ufw allow 26656/tcp

# Allow RPC (optional, only if serving RPC publicly)
# sudo ufw allow 26657/tcp

# Enable firewall
sudo ufw enable
```

### Bandwidth

| Activity | Bandwidth Usage |
|----------|-----------------|
| Initial sync (fast sync) | High (downloading blocks) |
| State sync | Moderate (downloading recent state) |
| Normal operation | 5-20 GB/day depending on peers |
| Serving RPC queries | Additional based on query volume |

## System Tuning

### Recommended sysctl Settings

```bash
# Add to /etc/sysctl.d/99-akash-node.conf
# Increase max open files
fs.file-max = 65535

# Network tuning
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.core.netdev_max_backlog = 65535

# Apply settings
sudo sysctl -p /etc/sysctl.d/99-akash-node.conf
```

### Recommended ulimits

```bash
# Add to /etc/security/limits.conf
* soft nofile 65535
* hard nofile 65535
* soft nproc 65535
* hard nproc 65535
```

## Choosing Between State Sync and Snapshot

| Method | Speed | Disk Usage During Sync | Complexity |
|--------|-------|------------------------|------------|
| State Sync | Fast (minutes) | Low | Moderate (configuration required) |
| Snapshot | Fast (depends on download) | Moderate (download + extract) | Low (download and extract) |
| Full Sync | Slow (days to weeks) | Grows during sync | Low (just start the node) |

- **State sync** is recommended for most users. It is fast and does not require downloading large files.
- **Snapshots** are a good alternative if state sync is unreliable or if you need a specific block height.
- **Full sync** from genesis is only needed for archive nodes or specific historical data requirements.

See [State Sync](./state-sync.md) for state sync configuration and snapshot download instructions.
