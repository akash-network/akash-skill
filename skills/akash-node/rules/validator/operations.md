# Validator Operations

## Overview

This guide covers day-to-day operations for Akash validators, including unjailing, commission management, governance participation, upgrades, and monitoring.

## Unjailing

A validator is jailed when it misses too many blocks (downtime) or commits a slashable offense. Jailed validators do not participate in consensus and do not earn rewards.

### Check Jail Status

```bash
# Check if your validator is jailed
akash query staking validator \
  $(akash keys show validator-wallet --bech val -a) \
  --output json | jq '{
    jailed: .jailed,
    status: .status,
    tokens: .tokens
  }'

# Check slashing info (includes jail duration and missed blocks)
akash query slashing signing-info \
  $(akash tendermint show-validator) \
  --output json | jq '{
    jailed_until: .jailed_until,
    tombstoned: .tombstoned,
    missed_blocks_counter: .missed_blocks_counter
  }'
```

### Unjail Your Validator

Before unjailing, ensure:

1. Your node is fully synced (`catching_up: false`).
2. The jail period has expired (check `jailed_until`).
3. The issue that caused jailing has been resolved.

```bash
# Unjail the validator
akash tx slashing unjail \
  --chain-id=akashnet-2 \
  --gas="auto" \
  --gas-adjustment=1.5 \
  --gas-prices="0.025uakt" \
  --from=validator-wallet \
  -y

# Verify the validator is no longer jailed
akash query staking validator \
  $(akash keys show validator-wallet --bech val -a) \
  --output json | jq '.jailed'
# Expected: false
```

### Common Jail Causes and Solutions

| Cause | Symptoms | Solution |
|-------|----------|----------|
| Node downtime | Missed blocks exceed threshold | Restart node, verify sync, then unjail |
| Stuck node | Node stopped producing/syncing | Check logs, restart, or resync |
| Network issues | P2P connectivity lost | Check firewall, peers, network |
| Software crash | Node process died | Check logs, update software, restart |
| Disk full | Write errors in logs | Free disk space, increase storage |
| Double signing | **Tombstoned (permanent)** | Cannot recover; must create new validator |

## Commission Changes

### View Current Commission

```bash
akash query staking validator \
  $(akash keys show validator-wallet --bech val -a) \
  --output json | jq '.commission'
```

### Change Commission Rate

```bash
# Change commission rate
akash tx staking edit-validator \
  --commission-rate="0.08" \
  --chain-id=akashnet-2 \
  --gas="auto" \
  --gas-adjustment=1.5 \
  --gas-prices="0.025uakt" \
  --from=validator-wallet \
  -y
```

### Commission Change Rules

| Rule | Description |
|------|-------------|
| Maximum rate | Cannot exceed `commission-max-rate` set at creation |
| Maximum change | Cannot exceed `commission-max-change-rate` per day |
| Cooldown | Can only change once every 24 hours |
| Visibility | Changes are visible on block explorers and to delegators |

## Delegation Management

### View Delegations

```bash
# View all delegations to your validator
akash query staking delegations-to \
  $(akash keys show validator-wallet --bech val -a)

# View your self-delegation
akash query staking delegation \
  $(akash keys show validator-wallet -a) \
  $(akash keys show validator-wallet --bech val -a)
```

### Withdraw Rewards

```bash
# Withdraw all rewards (commission + self-delegation rewards)
akash tx distribution withdraw-rewards \
  $(akash keys show validator-wallet --bech val -a) \
  --commission \
  --chain-id=akashnet-2 \
  --gas="auto" \
  --gas-adjustment=1.5 \
  --gas-prices="0.025uakt" \
  --from=validator-wallet \
  -y

# Withdraw only self-delegation rewards (without commission)
akash tx distribution withdraw-rewards \
  $(akash keys show validator-wallet --bech val -a) \
  --chain-id=akashnet-2 \
  --gas="auto" \
  --gas-adjustment=1.5 \
  --gas-prices="0.025uakt" \
  --from=validator-wallet \
  -y

# Query outstanding rewards
akash query distribution rewards \
  $(akash keys show validator-wallet -a)

# Query validator commission
akash query distribution commission \
  $(akash keys show validator-wallet --bech val -a)
```

### Redelegate Tokens

```bash
# Redelegate from one validator to another (no unbonding period)
akash tx staking redelegate \
  source_validator_operator_address \
  destination_validator_operator_address \
  1000000uakt \
  --chain-id=akashnet-2 \
  --gas="auto" \
  --gas-adjustment=1.5 \
  --gas-prices="0.025uakt" \
  --from=validator-wallet \
  -y
```

## Governance Voting

Validators are expected to participate actively in governance. Delegators often evaluate validators based on their governance participation.

### View Active Proposals

```bash
# List all active proposals
akash query gov proposals --status voting_period

# View a specific proposal
akash query gov proposal PROPOSAL_ID

# View proposal details
akash query gov proposal PROPOSAL_ID --output json | jq '{
  id: .id,
  title: .title,
  status: .status,
  voting_end_time: .voting_end_time,
  type: .content."@type"
}'
```

### Vote on a Proposal

```bash
# Vote options: yes, no, abstain, no_with_veto
akash tx gov vote PROPOSAL_ID yes \
  --chain-id=akashnet-2 \
  --gas="auto" \
  --gas-adjustment=1.5 \
  --gas-prices="0.025uakt" \
  --from=validator-wallet \
  -y
```

### Vote Options

| Option | Meaning |
|--------|---------|
| `yes` | Support the proposal |
| `no` | Oppose the proposal |
| `abstain` | Decline to vote for or against, but count toward quorum |
| `no_with_veto` | Strongly oppose; if >33.4% of votes are NoWithVeto, the proposal is vetoed and the deposit is burned |

### Weighted Voting

```bash
# Cast a weighted vote (split across multiple options)
akash tx gov weighted-vote PROPOSAL_ID \
  "yes=0.6,no=0.0,abstain=0.3,no_with_veto=0.1" \
  --chain-id=akashnet-2 \
  --gas="auto" \
  --gas-adjustment=1.5 \
  --gas-prices="0.025uakt" \
  --from=validator-wallet \
  -y
```

## Chain Upgrades with Cosmovisor

Cosmovisor is the recommended tool for managing chain upgrades automatically. It monitors the chain for upgrade proposals and swaps the binary when an upgrade height is reached.

### Installing Cosmovisor

```bash
# Install cosmovisor
go install cosmossdk.io/tools/cosmovisor/cmd/cosmovisor@latest

# Verify installation
cosmovisor version
```

### Setting Up Cosmovisor

```bash
# Set environment variables (add to ~/.bashrc or ~/.profile)
export DAEMON_NAME=akash
export DAEMON_HOME=$HOME/.akash
export DAEMON_ALLOW_DOWNLOAD_BINARIES=false
export DAEMON_RESTART_AFTER_UPGRADE=true
export DAEMON_LOG_BUFFER_SIZE=512
export UNSAFE_SKIP_BACKUP=false

# Create the cosmovisor directory structure
mkdir -p $DAEMON_HOME/cosmovisor/genesis/bin
mkdir -p $DAEMON_HOME/cosmovisor/upgrades

# Copy the current binary to cosmovisor genesis
cp $(which akash) $DAEMON_HOME/cosmovisor/genesis/bin/akash

# Verify
cosmovisor run version
```

### Cosmovisor Directory Structure

```
~/.akash/cosmovisor/
├── genesis/
│   └── bin/
│       └── akash         # Initial binary
├── upgrades/
│   ├── upgrade-v0.36.0/
│   │   └── bin/
│   │       └── akash     # Upgrade binary
│   └── upgrade-v0.38.0/
│       └── bin/
│           └── akash     # Future upgrade binary
└── current -> genesis/   # Symlink to active version
```

### Cosmovisor systemd Service

Replace the standard akash-node service with a cosmovisor-managed service:

```bash
sudo tee /etc/systemd/system/akash-node.service > /dev/null << 'EOF'
[Unit]
Description=Akash Node (Cosmovisor)
After=network-online.target

[Service]
User=akash
Group=akash
ExecStart=/home/akash/go/bin/cosmovisor run start --home /home/akash/.akash
Restart=on-failure
RestartSec=10
LimitNOFILE=65535
LimitNPROC=65535

# Cosmovisor environment
Environment="DAEMON_NAME=akash"
Environment="DAEMON_HOME=/home/akash/.akash"
Environment="DAEMON_ALLOW_DOWNLOAD_BINARIES=false"
Environment="DAEMON_RESTART_AFTER_UPGRADE=true"
Environment="DAEMON_LOG_BUFFER_SIZE=512"
Environment="UNSAFE_SKIP_BACKUP=false"

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=akash-node

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl restart akash-node
```

### Preparing for an Upgrade

When a governance proposal for a chain upgrade passes:

```bash
# 1. Check the upgrade proposal for the upgrade name and height
akash query gov proposal PROPOSAL_ID --output json | jq '.content'

# 2. Download or build the new binary
UPGRADE_NAME="v0.38.0"
NEW_VERSION="v0.38.0"

# Download pre-built binary
wget "https://github.com/akash-network/node/releases/download/${NEW_VERSION}/akash_linux_amd64.zip"
unzip akash_linux_amd64.zip

# Or build from source
git clone https://github.com/akash-network/node.git
cd node && git checkout "$NEW_VERSION" && make build

# 3. Place the new binary in the cosmovisor upgrades directory
mkdir -p ~/.akash/cosmovisor/upgrades/${UPGRADE_NAME}/bin
cp akash ~/.akash/cosmovisor/upgrades/${UPGRADE_NAME}/bin/akash

# 4. Verify the upgrade binary
~/.akash/cosmovisor/upgrades/${UPGRADE_NAME}/bin/akash version

# 5. Cosmovisor will automatically switch at the upgrade height
# Monitor logs during the upgrade
sudo journalctl -u akash-node -f --no-hostname -o cat
```

### Manual Upgrade (Without Cosmovisor)

If not using cosmovisor:

```bash
# 1. Wait for the node to halt at the upgrade height
# 2. Stop the node
sudo systemctl stop akash-node

# 3. Replace the binary
sudo cp akash-new-version /usr/local/bin/akash

# 4. Verify the version
akash version

# 5. Start the node
sudo systemctl start akash-node

# 6. Monitor logs
sudo journalctl -u akash-node -f --no-hostname -o cat
```

## Monitoring Validator Status

### Key Metrics to Monitor

| Metric | Command | Healthy Value |
|--------|---------|---------------|
| Sync status | `akash status 2>&1 \| jq '.SyncInfo.catching_up'` | `false` |
| Latest block height | `akash status 2>&1 \| jq '.SyncInfo.latest_block_height'` | Increasing |
| Peer count | `curl -s localhost:26657/net_info \| jq '.result.n_peers'` | > 5 |
| Validator jailed | `akash q staking validator $(akash keys show val -a --bech val) -o json \| jq '.jailed'` | `false` |
| Missed blocks | `akash q slashing signing-info $(akash tendermint show-validator) -o json \| jq '.missed_blocks_counter'` | Low (< 50) |
| Voting power | `akash status 2>&1 \| jq '.ValidatorInfo.VotingPower'` | > 0 |
| Disk usage | `du -sh ~/.akash/data/` | Below 80% capacity |

### Monitoring Script

```bash
#!/bin/bash
# validator-monitor.sh - Basic validator monitoring script

VALIDATOR_ADDR=$(akash keys show validator-wallet --bech val -a 2>/dev/null)
ALERT_EMAIL="alerts@example.com"

# Check if node is running
if ! systemctl is-active --quiet akash-node; then
  echo "ALERT: Akash node is not running!"
  # Add alerting here (email, Slack, PagerDuty, etc.)
  exit 1
fi

# Check sync status
CATCHING_UP=$(akash status 2>&1 | jq -r '.SyncInfo.catching_up')
if [ "$CATCHING_UP" = "true" ]; then
  echo "WARNING: Node is still catching up"
fi

# Check if jailed
JAILED=$(akash query staking validator "$VALIDATOR_ADDR" --output json 2>/dev/null | jq -r '.jailed')
if [ "$JAILED" = "true" ]; then
  echo "CRITICAL: Validator is jailed!"
fi

# Check missed blocks
MISSED=$(akash query slashing signing-info $(akash tendermint show-validator) --output json 2>/dev/null | jq -r '.missed_blocks_counter')
if [ "$MISSED" -gt 50 ]; then
  echo "WARNING: Missed $MISSED blocks"
fi

# Check peer count
PEERS=$(curl -s localhost:26657/net_info 2>/dev/null | jq -r '.result.n_peers')
if [ "$PEERS" -lt 3 ]; then
  echo "WARNING: Only $PEERS peers connected"
fi

# Check disk usage
DISK_USAGE=$(df -h ~/.akash/data/ | awk 'NR==2{print $5}' | tr -d '%')
if [ "$DISK_USAGE" -gt 80 ]; then
  echo "WARNING: Disk usage is at ${DISK_USAGE}%"
fi

# Output summary
echo "=== Validator Status ==="
echo "Synced:        $([ "$CATCHING_UP" = "false" ] && echo "Yes" || echo "No")"
echo "Jailed:        $JAILED"
echo "Missed Blocks: $MISSED"
echo "Peers:         $PEERS"
echo "Disk Usage:    ${DISK_USAGE}%"
BLOCK_HEIGHT=$(akash status 2>&1 | jq -r '.SyncInfo.latest_block_height')
echo "Block Height:  $BLOCK_HEIGHT"
```

Set up as a cron job:

```bash
# Run every 5 minutes
*/5 * * * * /home/akash/validator-monitor.sh >> /home/akash/monitor.log 2>&1
```

## Useful CLI Commands

### Node Information

```bash
# Full node status
akash status 2>&1 | jq

# Node ID
akash tendermint show-node-id

# Validator public key
akash tendermint show-validator

# Node version
akash version --long
```

### Staking Queries

```bash
# List all active validators
akash query staking validators --status bonded --output json | jq '.validators[] | {moniker: .description.moniker, tokens: .tokens, commission: .commission.commission_rates.rate}' | head -50

# Your validator info
akash query staking validator $(akash keys show validator-wallet --bech val -a)

# All delegations to your validator
akash query staking delegations-to $(akash keys show validator-wallet --bech val -a)

# Your delegations (where you have delegated)
akash query staking delegations $(akash keys show validator-wallet -a)

# Unbonding delegations
akash query staking unbonding-delegations $(akash keys show validator-wallet -a)

# Staking parameters
akash query staking params
```

### Distribution Queries

```bash
# Outstanding rewards
akash query distribution rewards $(akash keys show validator-wallet -a)

# Validator commission
akash query distribution commission $(akash keys show validator-wallet --bech val -a)

# Community pool
akash query distribution community-pool
```

### Slashing Queries

```bash
# Signing info for your validator
akash query slashing signing-info $(akash tendermint show-validator)

# Slashing parameters
akash query slashing params
```

### Transaction Queries

```bash
# Query a transaction by hash
akash query tx TX_HASH

# Query transactions by events
akash query txs --events='message.sender=akash1...'

# Query account balance
akash query bank balances $(akash keys show validator-wallet -a)
```

### Governance Queries

```bash
# List all proposals
akash query gov proposals

# Active proposals
akash query gov proposals --status voting_period

# View your vote on a proposal
akash query gov vote PROPOSAL_ID $(akash keys show validator-wallet -a)

# Governance parameters
akash query gov params
```

### Key Management

```bash
# List all keys
akash keys list

# Show key details
akash keys show validator-wallet

# Show validator operator address (valoper)
akash keys show validator-wallet --bech val -a

# Show validator consensus address
akash keys show validator-wallet --bech cons -a

# Export key (encrypted)
akash keys export validator-wallet

# Import key
akash keys import validator-wallet keyfile
```

## Operational Checklist

### Daily

| Task | Description |
|------|-------------|
| Check validator status | Verify the validator is bonded, not jailed |
| Monitor missed blocks | Ensure missed block count is low |
| Check disk usage | Verify sufficient disk space |
| Review logs | Look for errors or warnings |
| Verify peer count | Ensure adequate peer connections |

### Weekly

| Task | Description |
|------|-------------|
| Withdraw rewards | Claim accumulated rewards and commission |
| Review governance | Check for new proposals and vote |
| Security updates | Apply OS and software security patches |
| Backup verification | Verify backups are current and recoverable |
| Performance review | Check resource usage trends |

### Monthly

| Task | Description |
|------|-------------|
| Key rotation | Rotate SSH keys and access credentials |
| Infrastructure review | Evaluate hardware adequacy |
| Prune data | Clean up old logs and temporary files |
| Test failover | Verify sentry node failover procedures |
| Community engagement | Participate in validator discussions |

### Upgrade Events

| Task | Description |
|------|-------------|
| Monitor governance | Watch for upgrade proposals |
| Test new binary | Test on testnet before mainnet |
| Prepare cosmovisor | Place upgrade binary in correct directory |
| Monitor upgrade | Watch logs during the upgrade height |
| Verify post-upgrade | Confirm node is producing blocks after upgrade |
