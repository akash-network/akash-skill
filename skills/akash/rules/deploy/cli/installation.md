# Akash CLI Installation

Install the Akash CLI for command-line deployments and management.

## Quick Install

### Linux/macOS (Recommended)

```bash
curl -sSfL https://get.akash.network | sh
```

### Homebrew (macOS)

```bash
brew tap akash-network/tap
brew install akash
```

### From Binary

Download from [GitHub Releases](https://github.com/akash-network/node/releases):

```bash
# Linux AMD64
wget https://github.com/akash-network/node/releases/download/v0.36.0/akash_0.36.0_linux_amd64.zip
unzip akash_0.36.0_linux_amd64.zip
sudo mv akash /usr/local/bin/

# macOS AMD64
wget https://github.com/akash-network/node/releases/download/v0.36.0/akash_0.36.0_darwin_amd64.zip
unzip akash_0.36.0_darwin_amd64.zip
sudo mv akash /usr/local/bin/

# macOS ARM64 (Apple Silicon)
wget https://github.com/akash-network/node/releases/download/v0.36.0/akash_0.36.0_darwin_arm64.zip
unzip akash_0.36.0_darwin_arm64.zip
sudo mv akash /usr/local/bin/
```

### From Source

```bash
git clone https://github.com/akash-network/node
cd node
git checkout v0.36.0
make install
```

## Verify Installation

```bash
akash version
```

Expected output:
```
v0.36.0
```

## Initial Configuration

### Set Default Node

```bash
akash config node https://rpc.akashnet.net:443
```

### Set Chain ID

```bash
akash config chain-id akashnet-2
```

### Set Output Format

```bash
akash config output json
```

### Set Keyring Backend

```bash
# For development (stores keys unencrypted)
akash config keyring-backend test

# For production (requires password)
akash config keyring-backend os
```

### View Configuration

```bash
akash config
```

## Environment Variables

Alternative to `akash config`:

```bash
export AKASH_NODE="https://rpc.akashnet.net:443"
export AKASH_CHAIN_ID="akashnet-2"
export AKASH_KEYRING_BACKEND="os"
export AKASH_OUTPUT="json"
```

Add to `~/.bashrc` or `~/.zshrc` for persistence.

## Configuration File

Settings are stored in `~/.akash/config/client.toml`:

```toml
chain-id = "akashnet-2"
keyring-backend = "os"
output = "json"
node = "https://rpc.akashnet.net:443"
broadcast-mode = "sync"
```

## Provider Proxy (Optional)

For provider communication, install the provider proxy:

```bash
curl -sSfL https://get.akash.network/provider | sh
```

This enables:
- Lease log streaming
- Interactive shell access
- Service status queries

## Shell Completion

### Bash

```bash
akash completion bash > /etc/bash_completion.d/akash
```

### Zsh

```bash
akash completion zsh > "${fpath[1]}/_akash"
```

### Fish

```bash
akash completion fish > ~/.config/fish/completions/akash.fish
```

## Troubleshooting

### Command Not Found

```bash
# Add to PATH
export PATH=$PATH:$(go env GOPATH)/bin

# Or move binary
sudo mv akash /usr/local/bin/
```

### Permission Denied

```bash
chmod +x akash
```

### Version Mismatch

Ensure CLI version matches network version:

```bash
# Check network version
akash query upgrade current-plan --node https://rpc.akashnet.net:443

# Update CLI if needed
curl -sSfL https://get.akash.network | sh
```

### Connection Refused

```bash
# Test RPC connection
curl https://rpc.akashnet.net:443/status

# Try alternative endpoints
akash config node https://akash-rpc.polkachu.com:443
```

## Multiple Environments

Use environment variables or aliases for different networks:

```bash
# Mainnet
alias akash-main='akash --node https://rpc.akashnet.net:443 --chain-id akashnet-2'

# Testnet/Sandbox
alias akash-test='akash --node https://rpc.sandbox-01.aksh.pw:443 --chain-id sandbox-01'
```

## Next Steps

- **@wallet-setup.md** - Create and manage wallets
- **@deployment-lifecycle.md** - Deploy applications
- **@common-commands.md** - Command reference
