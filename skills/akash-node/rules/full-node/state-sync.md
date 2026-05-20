# State Sync Configuration

## What is State Sync

State sync is a feature in Tendermint/CometBFT that allows a new node to bootstrap quickly by downloading a recent application state snapshot from peers, rather than replaying all blocks from genesis. This dramatically reduces the time needed to get a node operational.

| Sync Method | Time to Sync | Data Downloaded | Historical Data |
|-------------|-------------|-----------------|-----------------|
| State Sync | Minutes | Small (recent state only) | No (only from trust height) |
| Snapshot | Minutes to hours | Moderate (compressed state) | No (depends on snapshot) |
| Full Sync | Days to weeks | Full chain history | Yes (all blocks from genesis) |

### How State Sync Works

1. The node contacts trusted RPC servers to obtain a recent block height and its hash (the "trust height" and "trust hash").
2. The node discovers peers that have state sync snapshots available.
3. The node downloads the application state snapshot at or near the trust height.
4. The node verifies the snapshot against the trusted hash.
5. The node begins normal block sync from the snapshot height onward.

### Limitations

- The node will not have historical block data before the snapshot height.
- Queries for historical transactions or blocks before the snapshot height will fail.
- State sync depends on peers having snapshots available and enabled.
- The trust height must be within the `trust_period` (typically 7 days).

## Prerequisites

Before configuring state sync, ensure:

- The Akash binary is installed and the node is initialized (`akash init`).
- The correct genesis file is in place.
- Seeds and/or persistent peers are configured.
- The data directory is clean (reset if necessary).

```bash
# Reset the node data if you have existing data
akash tendermint unsafe-reset-all --home ~/.akash --keep-addr-book
```

## Finding Trust Height and Hash

You need a recent block height and its hash from a trusted RPC endpoint. The trust height should be a few thousand blocks behind the latest height.

### Using a Public RPC Endpoint

```bash
# Set the RPC endpoint (use a trusted, reliable endpoint)
SNAP_RPC="https://rpc.akash.network:443"

# Get the latest block height
LATEST_HEIGHT=$(curl -s "$SNAP_RPC/block" | jq -r .result.block.header.height)
echo "Latest Height: $LATEST_HEIGHT"

# Calculate trust height (latest height minus a buffer)
# Use 2000 blocks as a safe buffer
TRUST_HEIGHT=$((LATEST_HEIGHT - 2000))
echo "Trust Height: $TRUST_HEIGHT"

# Get the hash at the trust height
TRUST_HASH=$(curl -s "$SNAP_RPC/block?height=$TRUST_HEIGHT" | jq -r .result.block_id.hash)
echo "Trust Hash: $TRUST_HASH"
```

### Using Multiple RPC Endpoints

For additional security, verify the trust hash from multiple independent RPC endpoints:

```bash
SNAP_RPC_1="https://rpc.akash.network:443"
SNAP_RPC_2="https://akash-rpc.polkachu.com:443"

HASH_1=$(curl -s "$SNAP_RPC_1/block?height=$TRUST_HEIGHT" | jq -r .result.block_id.hash)
HASH_2=$(curl -s "$SNAP_RPC_2/block?height=$TRUST_HEIGHT" | jq -r .result.block_id.hash)

echo "Hash from RPC 1: $HASH_1"
echo "Hash from RPC 2: $HASH_2"

if [ "$HASH_1" = "$HASH_2" ]; then
  echo "Hashes match - safe to proceed"
  TRUST_HASH="$HASH_1"
else
  echo "WARNING: Hashes do not match! Investigate before proceeding."
fi
```

## Configuring State Sync

### Automated Configuration

```bash
SNAP_RPC="https://rpc.akash.network:443"

# Calculate trust height and hash
LATEST_HEIGHT=$(curl -s "$SNAP_RPC/block" | jq -r .result.block.header.height)
TRUST_HEIGHT=$((LATEST_HEIGHT - 2000))
TRUST_HASH=$(curl -s "$SNAP_RPC/block?height=$TRUST_HEIGHT" | jq -r .result.block_id.hash)

# Apply state sync configuration to config.toml
sed -i '/\[statesync\]/,/^\[/{
  s/^enable *=.*/enable = true/
  s|^rpc_servers *=.*|rpc_servers = "'"$SNAP_RPC"','"$SNAP_RPC"'"|
  s/^trust_height *=.*/trust_height = '"$TRUST_HEIGHT"'/
  s/^trust_hash *=.*/trust_hash = "'"$TRUST_HASH"'"/
  s/^trust_period *=.*/trust_period = "168h0m0s"/
  s/^discovery_time *=.*/discovery_time = "15s"/
  s/^chunk_request_timeout *=.*/chunk_request_timeout = "10s"/
}' ~/.akash/config/config.toml
```

### Manual Configuration

Edit `~/.akash/config/config.toml` and locate the `[statesync]` section:

```toml
#######################################################
###         State Sync Configuration Options        ###
#######################################################
[statesync]

# State sync rapidly bootstraps a new node by discovering, fetching,
# and restoring a state machine snapshot from peers.
enable = true

# RPC servers (comma-separated) for light client verification of the
# synced state machine and target block. Also used for determining
# trusted block height and hash.
rpc_servers = "https://rpc.akash.network:443,https://akash-rpc.polkachu.com:443"

# Trust height - a recent verified block height.
# Should be within the trust_period from the current time.
trust_height = 18500000

# Trust hash - the block hash at trust_height.
# Obtained from a trusted RPC endpoint.
trust_hash = "ABCDEF1234567890ABCDEF1234567890ABCDEF1234567890ABCDEF1234567890"

# Trust period - maximum age of the trust height.
# Should match or be less than the chain's unbonding period.
trust_period = "168h0m0s"

# Time to spend discovering snapshots before initiating a restore.
discovery_time = "15s"

# Timeout for individual chunk requests during restore.
chunk_request_timeout = "10s"

# Number of chunk fetchers to run concurrently.
chunk_fetchers = "4"

# Temporary directory for state sync snapshot chunks.
# Defaults to the OS temp dir if empty.
temp_dir = ""
```

### Configuration Parameters Explained

| Parameter | Description | Recommended Value |
|-----------|-------------|-------------------|
| `enable` | Enable state sync | `true` |
| `rpc_servers` | Comma-separated list of trusted RPC endpoints | At least 2 endpoints |
| `trust_height` | A verified block height | Latest height minus 2000 |
| `trust_hash` | Block hash at trust_height | From trusted RPC |
| `trust_period` | Max age of trust height | `168h0m0s` (7 days) |
| `discovery_time` | Time to find snapshot peers | `15s` |
| `chunk_request_timeout` | Timeout per chunk download | `10s` |
| `chunk_fetchers` | Concurrent chunk downloads | `4` |

## Starting the Node with State Sync

```bash
# Ensure the data directory is clean
akash tendermint unsafe-reset-all --home ~/.akash --keep-addr-book

# Start the node (or restart the systemd service)
sudo systemctl restart akash-node

# Monitor the logs
sudo journalctl -u akash-node -f --no-hostname -o cat
```

### Expected Log Output

During state sync, you should see log entries similar to:

```
Discovering snapshots for 15s
Discovered new snapshot    height=18500000 format=1
Offering snapshot to ABCI app  height=18500000 format=1
Snapshot accepted, restoring  height=18500000 format=1
Applied snapshot chunk       height=18500000 format=1 chunk=0 total=50
Applied snapshot chunk       height=18500000 format=1 chunk=1 total=50
...
Snapshot restored           height=18500000 format=1
State sync complete, starting normal block sync
```

## Alternative: Snapshot Download

If state sync is unreliable or peers do not have snapshots available, you can download a snapshot from a snapshot provider.

### Using a Snapshot

```bash
# Stop the node
sudo systemctl stop akash-node

# Reset the data directory
akash tendermint unsafe-reset-all --home ~/.akash --keep-addr-book

# Download the snapshot (check community resources for current URLs)
# Common snapshot providers for Akash:
# - Polkachu
# - NodeStake
# - AutoStake

# Example download and extraction
SNAPSHOT_URL="https://snapshots.polkachu.com/snapshots/akash/akash_18500000.tar.lz4"
cd ~/.akash

# Download and extract in one step (saves disk space)
curl -L "$SNAPSHOT_URL" | lz4 -dc - | tar -xf -

# Or download first, then extract
wget "$SNAPSHOT_URL" -O akash_snapshot.tar.lz4
lz4 -dc akash_snapshot.tar.lz4 | tar -xf -
rm akash_snapshot.tar.lz4

# Start the node
sudo systemctl start akash-node
```

### Snapshot vs State Sync Comparison

| Factor | State Sync | Snapshot Download |
|--------|-----------|-------------------|
| Speed | Fast (minutes) | Depends on download speed |
| Reliability | Depends on peer availability | Depends on snapshot provider |
| Disk usage during bootstrap | Low | Higher (download + extract) |
| Configuration | Moderate (config.toml changes) | Low (download and extract) |
| Trust model | Verifies against RPC endpoints | Trust the snapshot provider |
| Availability | Always (if peers have snapshots) | Depends on provider uptime |

## Verifying Sync

After bootstrapping via state sync or snapshot, verify that the node is syncing correctly.

```bash
# Check sync status
akash status 2>&1 | jq '.SyncInfo'

# The node should show:
# - "catching_up": true (initially, while catching up to current height)
# - "catching_up": false (once fully synced)
# - "latest_block_height" should be increasing

# Check the latest block height and compare with a public RPC
LOCAL_HEIGHT=$(akash status 2>&1 | jq -r '.SyncInfo.latest_block_height')
NETWORK_HEIGHT=$(curl -s "https://rpc.akash.network:443/block" | jq -r .result.block.header.height)

echo "Local Height:   $LOCAL_HEIGHT"
echo "Network Height: $NETWORK_HEIGHT"
echo "Blocks Behind:  $((NETWORK_HEIGHT - LOCAL_HEIGHT))"
```

## Troubleshooting State Sync

| Issue | Cause | Solution |
|-------|-------|----------|
| No snapshots found | Peers don't have snapshots enabled | Try different RPC servers, or use a snapshot download |
| `trust hash mismatch` | Wrong trust hash or height | Recalculate trust height and hash |
| `trust height too old` | Trust height is outside trust period | Use a more recent trust height |
| Chunks timing out | Slow peers or network issues | Increase `chunk_request_timeout`, try different peers |
| `panic: failed to restore snapshot` | Corrupted snapshot data | Reset data and retry |
| Node stalls after state sync | Missing peers for block sync | Add more persistent peers |

### Resetting State Sync Configuration

After a successful state sync, disable state sync to prevent re-syncing on restart:

```bash
# Disable state sync after successful bootstrap
sed -i '/\[statesync\]/,/^\[/{
  s/^enable *=.*/enable = false/
}' ~/.akash/config/config.toml

# Restart the node
sudo systemctl restart akash-node
```

This prevents the node from attempting state sync again if the data directory is intact.
