# Full Node Installation Guide

## Overview

This guide covers installing and running an Akash full node on the `akashnet-2` mainnet. Follow each section in order.

## Step 1: Install the Akash Binary

### Option A: Download Pre-built Binary

```bash
# Set the version (check https://github.com/akash-network/node/releases for latest)
AKASH_VERSION="v0.36.0"

# Download the binary
wget "https://github.com/akash-network/node/releases/download/${AKASH_VERSION}/akash_linux_amd64.zip"

# Extract
unzip akash_linux_amd64.zip

# Move to system path
sudo mv akash /usr/local/bin/

# Verify installation
akash version
```

### Option B: Build from Source

```bash
# Clone the repository
git clone https://github.com/akash-network/node.git
cd node

# Checkout the desired version
AKASH_VERSION="v0.36.0"
git checkout "$AKASH_VERSION"

# Build
make install

# Verify installation (binary is in $GOPATH/bin)
akash version
```

## Step 2: Initialize the Node

```bash
# Set your moniker (node name)
MONIKER="my-akash-node"

# Initialize the node
akash init "$MONIKER" --chain-id akashnet-2

# This creates the following directory structure:
# ~/.akash/
# ├── config/
# │   ├── app.toml        # Application configuration
# │   ├── config.toml      # Tendermint configuration
# │   ├── genesis.json     # Chain genesis (will be replaced)
# │   ├── node_key.json    # Node identity key
# │   └── priv_validator_key.json  # Validator key (important for validators)
# └── data/
#     └── priv_validator_state.json
```

## Step 3: Download Genesis File

```bash
# Download the genesis file for akashnet-2
curl -s "https://raw.githubusercontent.com/akash-network/net/main/mainnet/genesis.json" > ~/.akash/config/genesis.json

# Verify the genesis file (check the hash matches known value)
sha256sum ~/.akash/config/genesis.json
```

## Step 4: Configure Seeds and Peers

### Set Seeds

Seeds are used for initial peer discovery. Add known seed nodes to your configuration.

```bash
# Set seed nodes in config.toml
SEEDS="node1@seed1.akash.network:26656,node2@seed2.akash.network:26656"
sed -i "s/^seeds *=.*/seeds = \"$SEEDS\"/" ~/.akash/config/config.toml
```

### Set Persistent Peers

Persistent peers are nodes your node will always try to maintain connections with.

```bash
# Set persistent peers
PEERS="peer1_id@peer1_ip:26656,peer2_id@peer2_ip:26656"
sed -i "s/^persistent_peers *=.*/persistent_peers = \"$PEERS\"/" ~/.akash/config/config.toml
```

**Tip:** Find current seeds and peers from the Akash Network community resources or the `akash-network/net` GitHub repository.

## Step 5: Configure the Node

### Minimum Gas Price

```bash
# Set minimum gas price in app.toml
sed -i 's/^minimum-gas-prices *=.*/minimum-gas-prices = "0.025uakt"/' ~/.akash/config/app.toml
```

### Pruning Configuration

```bash
# For a standard full node (moderate storage usage)
sed -i 's/^pruning *=.*/pruning = "custom"/' ~/.akash/config/app.toml
sed -i 's/^pruning-keep-recent *=.*/pruning-keep-recent = "100"/' ~/.akash/config/app.toml
sed -i 's/^pruning-interval *=.*/pruning-interval = "10"/' ~/.akash/config/app.toml
sed -i 's/^pruning-keep-every *=.*/pruning-keep-every = "0"/' ~/.akash/config/app.toml
```

### Additional Configuration

Edit `~/.akash/config/config.toml` for Tendermint settings:

```toml
# Indexer configuration
# Set to "null" to disable indexing (saves disk space)
# Set to "kv" to enable transaction indexing
[tx_index]
indexer = "kv"

# Mempool configuration
[mempool]
size = 5000
max_txs_bytes = 1073741824

# P2P configuration
[p2p]
max_num_inbound_peers = 40
max_num_outbound_peers = 10
```

Edit `~/.akash/config/app.toml` for application settings:

```toml
# API configuration
[api]
enable = true
swagger = false
address = "tcp://0.0.0.0:1317"

# gRPC configuration
[grpc]
enable = true
address = "0.0.0.0:9090"

# State sync snapshot configuration
[state-sync]
snapshot-interval = 0
snapshot-keep-recent = 2
```

## Step 6: Bootstrap the Node

Choose one of the following methods to bootstrap your node. State sync and snapshots are much faster than syncing from genesis.

### Option A: State Sync (Recommended)

See the detailed [State Sync Guide](./state-sync.md) for complete instructions.

Quick overview:

```bash
# Get a trust height and hash from a trusted RPC endpoint
SNAP_RPC="https://rpc.akash.network:443"

LATEST_HEIGHT=$(curl -s "$SNAP_RPC/block" | jq -r .result.block.header.height)
TRUST_HEIGHT=$((LATEST_HEIGHT - 2000))
TRUST_HASH=$(curl -s "$SNAP_RPC/block?height=$TRUST_HEIGHT" | jq -r .result.block_id.hash)

echo "Trust Height: $TRUST_HEIGHT"
echo "Trust Hash: $TRUST_HASH"

# Configure state sync in config.toml
sed -i "s/^enable *=.*/enable = true/" ~/.akash/config/config.toml
sed -i "s|^rpc_servers *=.*|rpc_servers = \"$SNAP_RPC,$SNAP_RPC\"|" ~/.akash/config/config.toml
sed -i "s/^trust_height *=.*/trust_height = $TRUST_HEIGHT/" ~/.akash/config/config.toml
sed -i "s/^trust_hash *=.*/trust_hash = \"$TRUST_HASH\"/" ~/.akash/config/config.toml
sed -i "s/^trust_period *=.*/trust_period = \"168h0m0s\"/" ~/.akash/config/config.toml
```

### Option B: Download Snapshot

```bash
# Stop the node if running
sudo systemctl stop akash-node

# Reset the data directory (preserves config)
akash tendermint unsafe-reset-all --home ~/.akash --keep-addr-book

# Download and extract a snapshot (check community resources for current URLs)
# Example using a snapshot provider:
SNAPSHOT_URL="https://snapshots.example.com/akash/latest.tar.lz4"
curl -L "$SNAPSHOT_URL" | lz4 -dc - | tar -xf - -C ~/.akash

# Start the node
sudo systemctl start akash-node
```

### Option C: Sync from Genesis (Slow)

Simply start the node without state sync or snapshot. The node will download and replay all blocks from genesis. This can take days or weeks.

```bash
akash start
```

## Step 7: Create systemd Service

Create a systemd service file to manage the Akash node as a background service.

```bash
sudo tee /etc/systemd/system/akash-node.service > /dev/null << 'EOF'
[Unit]
Description=Akash Node
After=network-online.target

[Service]
User=akash
Group=akash
ExecStart=/usr/local/bin/akash start --home /home/akash/.akash
Restart=on-failure
RestartSec=10
LimitNOFILE=65535
LimitNPROC=65535

# Environment variables
Environment="DAEMON_HOME=/home/akash/.akash"
Environment="DAEMON_NAME=akash"

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=akash-node

[Install]
WantedBy=multi-user.target
EOF
```

Enable and start the service:

```bash
# Create the akash user (if not already existing)
sudo useradd -m -s /bin/bash akash

# Set ownership of the data directory
sudo chown -R akash:akash /home/akash/.akash

# Reload systemd
sudo systemctl daemon-reload

# Enable the service to start on boot
sudo systemctl enable akash-node

# Start the service
sudo systemctl start akash-node

# Check service status
sudo systemctl status akash-node

# View logs
sudo journalctl -u akash-node -f --no-hostname -o cat
```

## Step 8: Verify Sync Status

### Check if the Node is Syncing

```bash
# Query the node's sync status
akash status 2>&1 | jq '.SyncInfo'
```

Expected output while syncing:

```json
{
  "latest_block_hash": "ABC123...",
  "latest_app_hash": "DEF456...",
  "latest_block_height": "12345678",
  "latest_block_time": "2024-01-15T10:30:00.000000000Z",
  "earliest_block_hash": "GHI789...",
  "earliest_app_hash": "JKL012...",
  "earliest_block_height": "12340000",
  "catching_up": true
}
```

**Key field:** `catching_up` -- when this is `false`, the node is fully synced.

### Monitor Sync Progress

```bash
# Watch sync progress (updates every 5 seconds)
while true; do
  STATUS=$(akash status 2>&1)
  CURRENT=$(echo "$STATUS" | jq -r '.SyncInfo.latest_block_height')
  CATCHING_UP=$(echo "$STATUS" | jq -r '.SyncInfo.catching_up')
  TIMESTAMP=$(echo "$STATUS" | jq -r '.SyncInfo.latest_block_time')
  echo "Height: $CURRENT | Catching Up: $CATCHING_UP | Block Time: $TIMESTAMP"
  sleep 5
done
```

### Verify Peer Connections

```bash
# Check connected peers
akash status 2>&1 | jq '.NodeInfo.network'

# Check number of peers
curl -s localhost:26657/net_info | jq '.result.n_peers'

# List connected peers
curl -s localhost:26657/net_info | jq '.result.peers[] | {node_id: .node_info.id, moniker: .node_info.moniker, remote_ip: .remote_ip}'
```

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Node not finding peers | Incorrect seeds/peers | Update seeds and peers from community resources |
| `appHash mismatch` | Data corruption or wrong binary version | Reset data and re-sync, verify binary version |
| Out of memory | Insufficient RAM | Increase RAM or adjust pruning settings |
| Disk full | Storage exhausted | Increase storage, enable pruning, or use pruned snapshots |
| `panic: failed to initialize database` | Corrupted database | Reset data directory and re-sync |
| Slow sync | Network or hardware bottleneck | Use state sync or snapshot instead of full sync |
| Connection refused on RPC | RPC not enabled or wrong bind address | Check `config.toml` laddr setting |

### Useful Diagnostic Commands

```bash
# Check node version
akash version --long

# Check node status
akash status

# View latest logs
sudo journalctl -u akash-node --since "5 minutes ago" --no-hostname -o cat

# Check disk usage
du -sh ~/.akash/data/

# Check system resources
htop
df -h
free -h

# Reset node data (keeps configuration)
akash tendermint unsafe-reset-all --home ~/.akash --keep-addr-book
```

### Resetting the Node

If you need to start fresh:

```bash
# Stop the service
sudo systemctl stop akash-node

# Reset data (preserves config and address book)
akash tendermint unsafe-reset-all --home ~/.akash --keep-addr-book

# OR: Full reset (removes everything except keys)
akash tendermint unsafe-reset-all --home ~/.akash

# Start the service again
sudo systemctl start akash-node
```
