# RPC Endpoints Reference

Public RPC and API endpoints for interacting with the Akash Network.

## Official Endpoints

### Akash Network (Mainnet)

| Service | URL |
|---------|-----|
| RPC | `https://rpc.akashnet.net:443` |
| REST/LCD | `https://api.akashnet.net:443` |
| gRPC | `grpc.akashnet.net:443` |

### Chain ID

```
akashnet-2
```

## Alternative RPC Providers

### Community Endpoints

| Provider | RPC | REST |
|----------|-----|------|
| Polkachu | `https://akash-rpc.polkachu.com:443` | `https://akash-api.polkachu.com:443` |
| Cosmos Directory | `https://rpc-akash.cosmos-spaces.cloud` | `https://api-akash.cosmos-spaces.cloud` |
| NodeStake | `https://rpc.akash.nodestake.org` | `https://api.akash.nodestake.org` |

### Archive Nodes

For historical queries:

| Provider | RPC |
|----------|-----|
| Polkachu | `https://akash-rpc.polkachu.com:443` |

## Using RPC Endpoints

### CLI Configuration

```bash
# Set default node
akash config node https://rpc.akashnet.net:443

# Or use per-command
akash query bank balances <address> --node https://rpc.akashnet.net:443
```

### SDK Configuration

**TypeScript:**
```typescript
import { createChainNodeSDK, createStargateClient } from "@akashnetwork/chain-sdk";

const signer = createStargateClient({
  baseUrl: "https://rpc.akashnet.net:443",
  signerMnemonic: process.env.MNEMONIC,
});

const sdk = createChainNodeSDK({
  query: { baseUrl: "http://grpc.akashnet.net:9090" },
  tx:    { signer },
});
```

**Go:**
```go
import "github.com/cosmos/cosmos-sdk/client"

clientCtx := client.Context{}.
    WithNodeURI("https://rpc.akashnet.net:443")
```

## API Types

### RPC (Tendermint)

For blockchain queries and transaction broadcast:

```bash
# Query block
curl https://rpc.akashnet.net/block?height=1000000

# Broadcast transaction
curl -X POST https://rpc.akashnet.net/broadcast_tx_commit \
  -d '{"tx": "..."}'
```

### REST/LCD (Cosmos SDK)

For account and module queries:

```bash
# Query account
curl https://api.akashnet.net/cosmos/auth/v1beta1/accounts/<address>

# Query deployments
curl https://api.akashnet.net/akash/deployment/v1beta3/deployments/list
```

### gRPC

For efficient binary protocol access:

```bash
# Using grpcurl
grpcurl -d '{"owner": "akash1..."}' \
  grpc.akashnet.net:443 \
  akash.deployment.v1beta3.Query/Deployments
```

## Console API

The Akash Console API provides additional functionality:

| Service | URL |
|---------|-----|
| Console API | `https://console-api.akash.network/v1` |
| Swagger Docs | `https://console-api.akash.network/v1/swagger` |

### Console API Endpoints

```bash
# Get deployment
GET https://console-api.akash.network/v1/deployment/<dseq>

# Validate SDL
POST https://console-api.akash.network/v1/sdl/validate

# Get providers
GET https://console-api.akash.network/v1/providers
```

## Provider Endpoints

Each provider exposes endpoints for lease management:

| Endpoint | Purpose |
|----------|---------|
| `/status` | Provider status |
| `/lease/<lease-id>/status` | Lease status |
| `/lease/<lease-id>/logs` | Container logs |
| `/lease/<lease-id>/shell` | Interactive shell |

### Accessing Provider Endpoints

Provider URLs are returned in lease info:

```bash
akash query market lease get \
  --owner <owner> \
  --dseq <dseq> \
  --gseq 1 \
  --oseq 1 \
  --provider <provider>
```

## WebSocket Endpoints

For real-time updates:

```
wss://rpc.akashnet.net/websocket
```

### Subscribe to Events

```javascript
const ws = new WebSocket('wss://rpc.akashnet.net/websocket');

ws.send(JSON.stringify({
  jsonrpc: '2.0',
  method: 'subscribe',
  params: ["tm.event='NewBlock'"],
  id: 1
}));
```

## Testnet Endpoints

For development and testing:

| Network | RPC | REST |
|---------|-----|------|
| Sandbox | `https://rpc.sandbox-01.aksh.pw:443` | `https://api.sandbox-01.aksh.pw:443` |

**Sandbox Chain ID:** `sandbox-01`

## Rate Limits

Public endpoints may have rate limits:

- **RPC**: Varies by provider
- **REST**: Varies by provider
- **Console API**: Check documentation

For high-volume applications:
1. Run your own node
2. Use multiple endpoints with failover
3. Contact providers for dedicated access

## Health Checks

### Check RPC Status

```bash
curl https://rpc.akashnet.net/status
```

### Check REST Status

```bash
curl https://api.akashnet.net/cosmos/base/tendermint/v1beta1/node_info
```

## Recommended Configuration

### High Availability Setup

Use multiple endpoints with failover:

```typescript
const endpoints = [
  "https://rpc.akashnet.net:443",
  "https://akash-rpc.polkachu.com:443",
  "https://rpc.akash.nodestake.org"
];

async function getRpcWithFallback() {
  for (const endpoint of endpoints) {
    try {
      const rpc = await getRpc(endpoint);
      return rpc;
    } catch (e) {
      console.warn(`Failed to connect to ${endpoint}`);
    }
  }
  throw new Error("All RPC endpoints failed");
}
```

### Local Development

Run a local node for development:

```bash
akash start --pruning nothing
```

Access at `http://localhost:26657` (RPC) and `http://localhost:1317` (REST).
