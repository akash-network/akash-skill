# Console API Overview

The Akash Console API provides REST endpoints for programmatic deployments and managed wallet operations.

## Base URL

```
https://console-api.akash.network/v1
```

## API Documentation

Full Swagger documentation:
```
https://console-api.akash.network/v1/swagger
```

## Key Features

| Feature | Description |
|---------|-------------|
| **Managed Wallets** | Create and manage wallets without handling keys |
| **Simplified Deployment** | Create deployments with single API call |
| **Provider Discovery** | List and filter available providers |
| **SDL Validation** | Validate SDL before deployment |
| **Lease Management** | Accept bids, close leases |

## Authentication

The Console API supports two authentication methods:

1. **API Key** - For server-to-server integrations
2. **JWT Token** - For user-authenticated requests

See **@authentication.md** for setup details.

## Core Endpoints

### Deployments

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/deployment` | Create new deployment |
| `GET` | `/deployment/{dseq}` | Get deployment details |
| `DELETE` | `/deployment/{dseq}` | Close deployment |
| `POST` | `/deployment/{dseq}/deposit` | Add funds to deployment |

### Providers

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/providers` | List all providers |
| `GET` | `/providers/{address}` | Get provider details |
| `GET` | `/providers/{address}/status` | Get provider status |

### Bids & Leases

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/bids/{dseq}` | List bids for deployment |
| `POST` | `/lease` | Accept bid and create lease |
| `GET` | `/lease/{dseq}/{gseq}/{oseq}` | Get lease details |
| `DELETE` | `/lease/{dseq}/{gseq}/{oseq}` | Close lease |

### SDL

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/sdl/validate` | Validate SDL syntax |
| `POST` | `/sdl/price` | Estimate deployment cost |

### Managed Wallet

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/wallet/create` | Create managed wallet |
| `GET` | `/wallet/balance` | Get wallet balance |
| `POST` | `/wallet/deposit` | Request deposit address |

## Quick Start

### 1. Get API Key

```bash
# Register at console.akash.network and generate API key
# Or use JWT from authenticated session
```

### 2. Validate SDL

```bash
curl -X POST https://console-api.akash.network/v1/sdl/validate \
  -H "Authorization: Bearer <api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "sdl": "version: \"2.0\"\nservices:\n  web:\n    image: nginx:1.25.3\n    expose:\n      - port: 80\n        to:\n          - global: true\nprofiles:\n  compute:\n    web:\n      resources:\n        cpu:\n          units: 0.5\n        memory:\n          size: 512Mi\n        storage:\n          size: 1Gi\n  placement:\n    dcloud:\n      pricing:\n        web:\n          denom: uact\n          amount: 1000\ndeployment:\n  web:\n    dcloud:\n      profile: web\n      count: 1"
  }'
```

### 3. Create Deployment

```bash
curl -X POST https://console-api.akash.network/v1/deployment \
  -H "Authorization: Bearer <api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "sdl": "<your-sdl>",
    "deposit": "5000000uact"
  }'
```

### 4. List Bids

```bash
curl https://console-api.akash.network/v1/bids/<dseq> \
  -H "Authorization: Bearer <api-key>"
```

### 5. Accept Bid

```bash
curl -X POST https://console-api.akash.network/v1/lease \
  -H "Authorization: Bearer <api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "dseq": "<dseq>",
    "gseq": 1,
    "oseq": 1,
    "provider": "<provider-address>"
  }'
```

## Response Format

### Success Response

```json
{
  "success": true,
  "data": {
    "dseq": "12345678",
    "owner": "akash1...",
    "state": "active"
  }
}
```

### Error Response

```json
{
  "success": false,
  "error": {
    "code": "INVALID_SDL",
    "message": "Invalid SDL: missing required field 'services'"
  }
}
```

## Rate Limits

| Tier | Requests/min | Deployments/day |
|------|--------------|-----------------|
| Free | 60 | 10 |
| Pro | 300 | 100 |
| Enterprise | Unlimited | Unlimited |

## Use Cases

### CI/CD Integration

```yaml
# GitHub Actions example
deploy:
  runs-on: ubuntu-latest
  steps:
    - name: Deploy to Akash
      run: |
        curl -X POST https://console-api.akash.network/v1/deployment \
          -H "Authorization: Bearer ${{ secrets.AKASH_API_KEY }}" \
          -d '{"sdl": "${{ env.SDL }}"}'
```

### Deployment Automation

```javascript
async function deployToAkash(sdl) {
  // Create deployment
  const deployment = await fetch('https://console-api.akash.network/v1/deployment', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${API_KEY}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ sdl, deposit: '5000000uact' })
  });

  const { data: { dseq } } = await deployment.json();

  // Wait for bids
  await new Promise(r => setTimeout(r, 30000));

  // Get bids
  const bids = await fetch(`https://console-api.akash.network/v1/bids/${dseq}`, {
    headers: { 'Authorization': `Bearer ${API_KEY}` }
  });

  // Accept lowest bid
  const { data: bidList } = await bids.json();
  const lowestBid = bidList.sort((a, b) => a.price - b.price)[0];

  await fetch('https://console-api.akash.network/v1/lease', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${API_KEY}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      dseq,
      gseq: 1,
      oseq: 1,
      provider: lowestBid.provider
    })
  });

  return dseq;
}
```

## SDK Support

For TypeScript/JavaScript applications, consider using the Console API via the SDK:

```typescript
import { ConsoleApiClient } from "@akashnetwork/console-api-client";

const client = new ConsoleApiClient({ apiKey: API_KEY });
const deployment = await client.createDeployment({ sdl });
```

## Related Documentation

- **@authentication.md** - API key and JWT setup
- **@managed-wallet.md** - Managed wallet operations
- **@deployment-endpoints.md** - Detailed endpoint reference
