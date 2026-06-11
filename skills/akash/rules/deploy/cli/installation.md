# Akash CLI Installation

Install the `provider-services` CLI for command-line deployments and provider interaction.

## Quick Install

### Linux/macOS (Recommended)

```bash
curl -sfL https://raw.githubusercontent.com/akash-network/provider/main/install.sh | bash
sudo mv ./bin/provider-services /usr/local/bin/
```

Or install straight to a directory:

```bash
curl -sfL https://raw.githubusercontent.com/akash-network/provider/main/install.sh | sudo bash -s -- -b /usr/local/bin
```

### Homebrew (macOS)

```bash
brew tap akash-network/tap
brew install akash-provider-services
```

### From Binary

This resolves the latest stable release automatically — no version to keep in sync.
(`/releases/latest` skips pre-releases/rc builds. Requires `curl` + `jq`.)

```bash
# Resolve the latest stable tag (e.g. v0.12.0) and the bare number (0.12.0)
VERSION=$(curl -s https://api.github.com/repos/akash-network/provider/releases/latest | jq -r .tag_name)
NUM=${VERSION#v}

# Pick your platform asset
ASSET="provider-services_${NUM}_linux_amd64.zip"   # Linux AMD64
# ASSET="provider-services_${NUM}_linux_arm64.zip" # Linux ARM64
# ASSET="provider-services_${NUM}_darwin_all.zip"  # macOS (universal)

wget "https://github.com/akash-network/provider/releases/download/${VERSION}/${ASSET}"
unzip "$ASSET"
sudo mv provider-services /usr/local/bin/
```

To pin a specific release instead, set `VERSION=v0.12.0` (and `NUM=0.12.0`) manually
— see [GitHub Releases](https://github.com/akash-network/provider/releases).

### From Source

```bash
git clone https://github.com/akash-network/provider
cd provider
make deps-install
make install
```

## Verify Installation

```bash
provider-services version
```

## Initial Configuration

`provider-services` has no `config` subcommand. Configure it with environment variables and/or per-command flags.

### Environment Variables

```bash
export AKASH_NODE="https://rpc.akashnet.net:443"
export AKASH_CHAIN_ID="akashnet-2"
export AKASH_KEYRING_BACKEND="os"     # use "test" for development (keys stored unencrypted)
export AKASH_GAS_PRICES="0.025uakt"
```

Add to `~/.bashrc` or `~/.zshrc` for persistence.

### Per-command Flags

Alternatively, pass values on each command:

```bash
--node https://rpc.akashnet.net:443
--chain-id akashnet-2
--keyring-backend os
--gas-prices 0.025uakt
```

## Provider Interaction

Provider communication is handled by `provider-services` itself (installed above):

```bash
curl -sfL https://raw.githubusercontent.com/akash-network/provider/main/install.sh | bash
sudo mv ./bin/provider-services /usr/local/bin/
```

This enables:
- Lease log streaming
- Interactive shell access
- Service status queries

## Shell Completion

### Bash

```bash
provider-services completion bash > /etc/bash_completion.d/provider-services
```

### Zsh

```bash
provider-services completion zsh > "${fpath[1]}/_provider-services"
```

### Fish

```bash
provider-services completion fish > ~/.config/fish/completions/provider-services.fish
```

## Troubleshooting

### Command Not Found

```bash
# Add to PATH
export PATH=$PATH:$(go env GOPATH)/bin

# Or move binary
sudo mv provider-services /usr/local/bin/
```

### Permission Denied

```bash
chmod +x provider-services
```

### Version Mismatch

Ensure CLI version matches network version:

```bash
# Check network version
provider-services query upgrade plan --node https://rpc.akashnet.net:443

# Update CLI if needed
curl -sfL https://raw.githubusercontent.com/akash-network/provider/main/install.sh | bash
sudo mv ./bin/provider-services /usr/local/bin/
```

### Connection Refused

```bash
# Test RPC connection
curl https://rpc.akashnet.net:443/status

# Try alternative endpoints
export AKASH_NODE=https://akash-rpc.polkachu.com:443
# or pass --node https://akash-rpc.polkachu.com:443 per command
```

## Multiple Environments

Use environment variables or aliases for different networks:

```bash
# Mainnet
alias akash-main='provider-services --node https://rpc.akashnet.net:443 --chain-id akashnet-2'

# Testnet/Sandbox
alias akash-test='provider-services --node https://rpc.sandbox-01.aksh.pw:443 --chain-id sandbox-01'
```

## Next Steps

- **@wallet-setup.md** - Create and manage wallets
- **@deployment-lifecycle.md** - Deploy applications
- **@common-commands.md** - Command reference
