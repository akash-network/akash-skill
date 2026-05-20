# Validator Security

## Overview

Validator security is critical for protecting staked tokens and maintaining the integrity of the Akash Network. A compromised validator key can lead to double-signing (permanent slashing and tombstoning) or extended downtime (jailing and slashing). This guide covers best practices for securing your validator infrastructure.

## Security Threat Model

| Threat | Impact | Mitigation |
|--------|--------|------------|
| Double signing | 5% slash, permanent tombstone | TMKMS, sentry nodes, never run duplicate validators |
| Downtime | 0.01% slash, temporary jail | Monitoring, redundant infrastructure, alerting |
| Key theft | Full validator compromise | TMKMS with HSM, encrypted backups, access control |
| DDoS attack | Node unreachable, downtime | Sentry node architecture, rate limiting |
| Unauthorized access | Server compromise | SSH hardening, firewalls, principle of least privilege |

## Sentry Node Architecture

The sentry node architecture protects your validator from direct exposure to the public network. Sentry nodes act as proxies, shielding the validator's IP address and absorbing DDoS attacks.

### Architecture Diagram

```
                    Internet
                       |
          +------------+------------+
          |            |            |
     +----v----+  +----v----+  +----v----+
     | Sentry  |  | Sentry  |  | Sentry  |
     | Node 1  |  | Node 2  |  | Node 3  |
     +----+----+  +----+----+  +----+----+
          |            |            |
          +-----+------+------+----+
                |             |
         +------v------+     |
         |  Validator  |-----+
         |    Node     |
         +-------------+
         (Private Network)
```

### Validator Node Configuration

The validator should only connect to its sentry nodes and never expose its P2P port publicly.

Edit `~/.akash/config/config.toml` on the **validator node**:

```toml
[p2p]
# Only connect to sentry nodes
persistent_peers = "sentry1_node_id@sentry1_private_ip:26656,sentry2_node_id@sentry2_private_ip:26656,sentry3_node_id@sentry3_private_ip:26656"

# Do not advertise the validator's address
addr_book_strict = false

# Disable peer exchange (PEX) so the validator doesn't discover public peers
pex = false

# Set the validator as unconditional peers on sentries
# (configured on sentry nodes, not here)
```

### Sentry Node Configuration

Edit `~/.akash/config/config.toml` on each **sentry node**:

```toml
[p2p]
# Include the validator as a persistent peer
persistent_peers = "validator_node_id@validator_private_ip:26656"

# Set the validator node ID as an unconditional peer
# This ensures the sentry always maintains connection to the validator
unconditional_peer_ids = "validator_node_id"

# Set the validator node ID as a private peer
# This prevents the sentry from gossiping the validator's address
private_peer_ids = "validator_node_id"

# Enable peer exchange for sentry nodes
pex = true
```

### Network Configuration

| Node | P2P Port (26656) | RPC Port (26657) | Public Internet |
|------|-------------------|-------------------|-----------------|
| Validator | Private only (sentries) | Localhost only | No direct access |
| Sentry 1 | Public | Optional | Yes |
| Sentry 2 | Public | Optional | Yes |
| Sentry 3 | Public | Optional | Yes |

## TMKMS (Tendermint Key Management System)

TMKMS is a key management system for Tendermint validators that provides:

- Remote signing: The validator key never resides on the validator node itself.
- HSM support: Integration with hardware security modules (YubiHSM2, Ledger).
- Double-sign protection: Built-in safeguards against signing conflicting blocks.
- Audit logging: All signing operations are logged.

### TMKMS Architecture

```
+-------------------+        +------------------+
|  Validator Node   |  TCP   |    TMKMS Server  |
|                   | <----> |                  |
| (no validator key)|        | (holds the key)  |
+-------------------+        +--+---------------+
                                 |
                          +------v------+
                          |   YubiHSM2  |
                          |   (optional)|
                          +-------------+
```

### Installing TMKMS

```bash
# Install Rust (required for TMKMS)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# Install TMKMS with softsign support
cargo install tmkms --features=softsign

# Or with YubiHSM support
cargo install tmkms --features=yubihsm

# Verify installation
tmkms version
```

### Initializing TMKMS

```bash
# Create TMKMS configuration directory
mkdir -p ~/.tmkms/akash
cd ~/.tmkms/akash

# Initialize TMKMS (generates configuration template)
tmkms init ~/.tmkms/akash
```

### TMKMS Configuration

Create or edit `~/.tmkms/akash/tmkms.toml`:

```toml
# TMKMS Configuration for Akash Validator

# Chain configuration
[[chain]]
id = "akashnet-2"
key_format = { type = "bech32", account_key_prefix = "akashpub", consensus_key_prefix = "akashvalconspub" }
state_file = "/home/tmkms/.tmkms/akash/state/akashnet-2-consensus.json"

# Software-based signing (softsign)
# For production, consider using YubiHSM2 instead
[[providers.softsign]]
chain_ids = ["akashnet-2"]
key_type = "consensus"
path = "/home/tmkms/.tmkms/akash/secrets/akashnet-2-consensus.key"

# YubiHSM2 configuration (uncomment for hardware signing)
# [[providers.yubihsm]]
# adapter = { type = "usb" }
# auth = { key = 1, password_file = "/home/tmkms/.tmkms/akash/secrets/yubihsm-password.txt" }
# keys = [{ chain_ids = ["akashnet-2"], key = 1 }]
# serial_number = "0123456789"

# Validator connection
[[validator]]
chain_id = "akashnet-2"
addr = "tcp://validator_ip:26659"
secret_key = "/home/tmkms/.tmkms/akash/secrets/kms-identity.key"
protocol_version = "v0.34"
reconnect = true
```

### Importing the Validator Key into TMKMS

```bash
# Import the existing validator key (softsign)
tmkms softsign import \
  ~/.akash/config/priv_validator_key.json \
  ~/.tmkms/akash/secrets/akashnet-2-consensus.key

# IMPORTANT: After importing, remove the key from the validator node
# Only do this after confirming TMKMS is working!
# mv ~/.akash/config/priv_validator_key.json ~/.akash/config/priv_validator_key.json.backup
```

### Configuring the Validator Node for TMKMS

Edit `~/.akash/config/config.toml` on the **validator node** to accept remote signing:

```toml
[priv_validator]
# TCP address for TMKMS connection
# The validator listens for incoming connections from TMKMS
laddr = "tcp://0.0.0.0:26659"

# Disable the local key file (TMKMS handles signing)
# key_file = "config/priv_validator_key.json"
# state_file = "data/priv_validator_state.json"
```

### Running TMKMS

```bash
# Start TMKMS
tmkms start -c ~/.tmkms/akash/tmkms.toml

# Or create a systemd service
sudo tee /etc/systemd/system/tmkms.service > /dev/null << 'EOF'
[Unit]
Description=Tendermint KMS
After=network-online.target

[Service]
User=tmkms
Group=tmkms
ExecStart=/home/tmkms/.cargo/bin/tmkms start -c /home/tmkms/.tmkms/akash/tmkms.toml
Restart=on-failure
RestartSec=3
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable tmkms
sudo systemctl start tmkms
```

### Verifying TMKMS

```bash
# Check TMKMS logs
sudo journalctl -u tmkms -f --no-hostname -o cat

# Expected output when connected:
# [info] tmkms 0.13.1 starting up...
# [info] [akashnet-2@tcp://validator_ip:26659] connected to validator successfully
# [info] [akashnet-2@tcp://validator_ip:26659] signed PreVote at height 18500001
```

## Key Backup Procedures

### Files to Back Up

| File | Location | Sensitivity | Purpose |
|------|----------|-------------|---------|
| `priv_validator_key.json` | `~/.akash/config/` | CRITICAL | Validator consensus key |
| `node_key.json` | `~/.akash/config/` | Important | Node identity |
| Wallet mnemonic | Offline only | CRITICAL | Wallet recovery |
| TMKMS key | `~/.tmkms/akash/secrets/` | CRITICAL | Signing key (if using TMKMS) |

### Backup Best Practices

1. **Encrypt all backups:** Use GPG or a hardware-encrypted storage device.

   ```bash
   # Encrypt the validator key with GPG
   gpg --symmetric --cipher-algo AES256 \
     ~/.akash/config/priv_validator_key.json
   # This creates priv_validator_key.json.gpg
   ```

2. **Store backups offline:** USB drives, safety deposit boxes, or other secure physical locations.

3. **Use multiple backup locations:** Keep copies in geographically separate locations.

4. **Test recovery:** Periodically verify that you can restore from your backups.

5. **Never store validator keys in:**
   - Cloud storage (Google Drive, Dropbox, etc.)
   - Git repositories
   - Unencrypted USB drives
   - Email

### Recovery Procedure

```bash
# Restore validator key from encrypted backup
gpg --decrypt priv_validator_key.json.gpg > ~/.akash/config/priv_validator_key.json

# Set correct permissions
chmod 600 ~/.akash/config/priv_validator_key.json

# Restore wallet from mnemonic
akash keys add validator-wallet --recover
# Enter your mnemonic when prompted
```

## Firewall Configuration

### Validator Node Firewall (UFW)

```bash
# Reset firewall rules
sudo ufw reset

# Default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (use a non-standard port for added security)
sudo ufw allow 22/tcp

# Allow P2P from sentry nodes only (if using sentry architecture)
sudo ufw allow from sentry1_ip to any port 26656 proto tcp
sudo ufw allow from sentry2_ip to any port 26656 proto tcp
sudo ufw allow from sentry3_ip to any port 26656 proto tcp

# Allow TMKMS connection (if TMKMS runs on a separate server)
sudo ufw allow from tmkms_ip to any port 26659 proto tcp

# DO NOT expose RPC (26657), REST (1317), or gRPC (9090) publicly on validators

# Enable firewall
sudo ufw enable

# Verify rules
sudo ufw status verbose
```

### Sentry Node Firewall (UFW)

```bash
# Reset firewall rules
sudo ufw reset

# Default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH
sudo ufw allow 22/tcp

# Allow P2P from everyone (sentry nodes are public-facing)
sudo ufw allow 26656/tcp

# Allow RPC (optional, if serving public RPC)
# sudo ufw allow 26657/tcp

# Enable firewall
sudo ufw enable
```

### SSH Hardening

```bash
# Edit SSH configuration
# /etc/ssh/sshd_config

# Disable root login
PermitRootLogin no

# Disable password authentication (use keys only)
PasswordAuthentication no

# Use a non-standard SSH port
Port 2222

# Allow only specific users
AllowUsers akash

# Restart SSH service
sudo systemctl restart sshd
```

## Monitoring for Double-Signing

Double-signing is the most severe slashing offense and results in permanent tombstoning. Prevention is critical.

### Prevention Strategies

| Strategy | Description |
|----------|-------------|
| Never run duplicate validators | Only one instance should have the validator key |
| Use TMKMS | Built-in double-sign protection |
| Monitor `priv_validator_state.json` | Track last signed height, round, and step |
| Lock out old nodes during migrations | Stop and disable old validator before starting new one |
| Use a single signing authority | TMKMS serves as the single source of truth for signing |

### Monitoring Tools

```bash
# Check if your validator has been slashed
akash query slashing signing-info \
  $(akash tendermint show-validator) \
  --output json | jq '{
    address: .address,
    start_height: .start_height,
    jailed_until: .jailed_until,
    tombstoned: .tombstoned,
    missed_blocks_counter: .missed_blocks_counter
  }'

# Monitor missed blocks
akash query slashing signing-info $(akash tendermint show-validator)
```

### Alerting

Set up alerts for the following conditions:

| Condition | Alert Level | Action |
|-----------|-------------|--------|
| Node is not syncing | Warning | Check node status, restart if needed |
| Missed > 50 blocks | Critical | Investigate immediately |
| Validator jailed | Critical | Identify cause, fix, then unjail |
| Tombstoned | Fatal | Validator is permanently disabled |
| Disk usage > 80% | Warning | Expand storage or increase pruning |
| Memory usage > 90% | Warning | Investigate memory leaks |
| Peer count < 3 | Warning | Check network connectivity |

### Prometheus Metrics

Enable Prometheus metrics in `~/.akash/config/config.toml`:

```toml
[instrumentation]
prometheus = true
prometheus_listen_addr = ":26660"
namespace = "akash"
```

Key metrics to monitor:

| Metric | Description |
|--------|-------------|
| `tendermint_consensus_height` | Current block height |
| `tendermint_consensus_validators` | Number of active validators |
| `tendermint_consensus_missing_validators` | Number of validators missing from round |
| `tendermint_consensus_rounds` | Number of rounds in current height |
| `tendermint_p2p_peers` | Number of connected peers |
| `tendermint_consensus_fast_syncing` | Whether the node is fast syncing |

## Security Checklist

| Item | Status |
|------|--------|
| Sentry node architecture deployed | |
| Validator P2P port restricted to sentry nodes only | |
| TMKMS configured and running | |
| Validator key removed from validator node (if using TMKMS) | |
| Encrypted backup of validator key stored offline | |
| Wallet mnemonic stored securely offline | |
| Firewall configured on all nodes | |
| SSH hardened (key-only, non-standard port) | |
| Monitoring and alerting configured | |
| Prometheus metrics enabled | |
| Automatic security updates enabled | |
| Separate user account for node (not root) | |
| Double-sign prevention verified | |
