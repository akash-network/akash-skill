# Deployment Endpoints Reference

Complete API reference for Console API deployment operations.

## Base URL

```
https://console-api.akash.network/v1
```

## Deployment Endpoints

### Create Deployment

Create a new deployment on Akash Network.

```http
POST /deployment
```

**Request Body:**
```json
{
  "sdl": "version: \"2.0\"\nservices:\n  web:\n    image: nginx:1.25.3...",
  "deposit": "5000000uact",
  "walletId": "wallet-123"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sdl` | string | Yes | SDL configuration (YAML as string) |
| `deposit` | string | Yes | Initial escrow deposit (e.g., "5000000uact") |
| `walletId` | string | No | Managed wallet ID (uses default if omitted) |

**Response:**
```json
{
  "success": true,
  "data": {
    "dseq": "12345678",
    "owner": "akash1abc...",
    "state": "open",
    "deposit": {
      "denom": "uact",
      "amount": "5000000"
    },
    "createdAt": "2024-01-15T10:00:00Z",
    "txHash": "ABC123..."
  }
}
```

**cURL Example:**
```bash
curl -X POST https://console-api.akash.network/v1/deployment \
  -H "Authorization: Bearer <api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "sdl": "version: \"2.0\"\nservices:\n  web:\n    image: nginx:1.25.3\n    expose:\n      - port: 80\n        to:\n          - global: true\nprofiles:\n  compute:\n    web:\n      resources:\n        cpu:\n          units: 0.5\n        memory:\n          size: 512Mi\n        storage:\n          size: 1Gi\n  placement:\n    dcloud:\n      pricing:\n        web:\n          denom: uact\n          amount: 1000\ndeployment:\n  web:\n    dcloud:\n      profile: web\n      count: 1",
    "deposit": "5000000uact"
  }'
```

### Get Deployment

Retrieve deployment details.

```http
GET /deployment/{dseq}
```

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `dseq` | string | Deployment sequence number |

**Response:**
```json
{
  "success": true,
  "data": {
    "dseq": "12345678",
    "owner": "akash1abc...",
    "state": "active",
    "deposit": {
      "denom": "uact",
      "amount": "4500000"
    },
    "escrowBalance": {
      "denom": "uact",
      "amount": "4000000"
    },
    "createdAt": "2024-01-15T10:00:00Z",
    "leases": [
      {
        "gseq": 1,
        "oseq": 1,
        "provider": "akash1prov...",
        "state": "active",
        "price": {
          "denom": "uact",
          "amount": "950"
        }
      }
    ]
  }
}
```

### List Deployments

List all deployments for your account.

```http
GET /deployments
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `state` | string | all | Filter by state (open, active, closed) |
| `limit` | number | 20 | Results per page |
| `offset` | number | 0 | Pagination offset |

**Response:**
```json
{
  "success": true,
  "data": {
    "deployments": [
      {
        "dseq": "12345678",
        "state": "active",
        "createdAt": "2024-01-15T10:00:00Z"
      }
    ],
    "pagination": {
      "total": 50,
      "limit": 20,
      "offset": 0
    }
  }
}
```

### Close Deployment

Close a deployment and return remaining escrow.

```http
DELETE /deployment/{dseq}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "dseq": "12345678",
    "state": "closed",
    "refundedAmount": {
      "denom": "uact",
      "amount": "3500000"
    },
    "txHash": "DEF456..."
  }
}
```

### Deposit to Deployment

Add funds to deployment escrow.

```http
POST /deployment/{dseq}/deposit
```

**Request Body:**
```json
{
  "amount": "5000000uact"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "dseq": "12345678",
    "newBalance": {
      "denom": "uact",
      "amount": "9000000"
    },
    "txHash": "GHI789..."
  }
}
```

### Update Deployment

Update deployment with new SDL.

```http
PUT /deployment/{dseq}
```

**Request Body:**
```json
{
  "sdl": "<updated-sdl>"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "dseq": "12345678",
    "state": "active",
    "txHash": "JKL012..."
  }
}
```

## Bid Endpoints

### List Bids

Get bids for a deployment.

```http
GET /bids/{dseq}
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `gseq` | number | 1 | Group sequence |

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "provider": "akash1prov1...",
      "price": {
        "denom": "uact",
        "amount": "950"
      },
      "state": "open",
      "createdAt": "2024-01-15T10:01:00Z",
      "attributes": {
        "region": "us-west",
        "host": "provider1"
      }
    },
    {
      "provider": "akash1prov2...",
      "price": {
        "denom": "uact",
        "amount": "1100"
      },
      "state": "open",
      "createdAt": "2024-01-15T10:01:30Z",
      "attributes": {
        "region": "eu-central",
        "host": "provider2"
      }
    }
  ]
}
```

## Lease Endpoints

### Create Lease

Accept a bid and create lease.

```http
POST /lease
```

**Request Body:**
```json
{
  "dseq": "12345678",
  "gseq": 1,
  "oseq": 1,
  "provider": "akash1prov..."
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "dseq": "12345678",
    "gseq": 1,
    "oseq": 1,
    "provider": "akash1prov...",
    "state": "active",
    "price": {
      "denom": "uact",
      "amount": "950"
    },
    "txHash": "MNO345..."
  }
}
```

### Get Lease

Get lease details.

```http
GET /lease/{dseq}/{gseq}/{oseq}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "dseq": "12345678",
    "gseq": 1,
    "oseq": 1,
    "provider": "akash1prov...",
    "state": "active",
    "price": {
      "denom": "uact",
      "amount": "950"
    },
    "services": {
      "web": {
        "name": "web",
        "available": 1,
        "total": 1,
        "uris": [
          "https://abc123.provider.akash.network"
        ]
      }
    }
  }
}
```

### Get Lease Status

Get detailed lease status including service information.

```http
GET /lease/{dseq}/{gseq}/{oseq}/status
```

**Response:**
```json
{
  "success": true,
  "data": {
    "services": {
      "web": {
        "name": "web",
        "available": 1,
        "total": 1,
        "readyReplicas": 1,
        "availableReplicas": 1,
        "observedGeneration": 1,
        "replicas": 1,
        "updatedReplicas": 1,
        "uris": [
          "https://abc123.ingress.provider.akash.network"
        ],
        "ips": null
      }
    },
    "forwardedPorts": {}
  }
}
```

### Close Lease

Close a specific lease.

```http
DELETE /lease/{dseq}/{gseq}/{oseq}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "dseq": "12345678",
    "gseq": 1,
    "oseq": 1,
    "state": "closed",
    "txHash": "PQR678..."
  }
}
```

### Get Lease Logs

Stream logs from deployment.

```http
GET /lease/{dseq}/{gseq}/{oseq}/logs
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `service` | string | all | Service name to filter |
| `follow` | boolean | false | Stream logs |
| `tail` | number | 100 | Number of lines |

**Response:** (text/plain for streaming)
```
2024-01-15T10:05:00Z web-0 nginx: 10.0.0.1 - - [15/Jan/2024:10:05:00 +0000] "GET / HTTP/1.1" 200 612
2024-01-15T10:05:01Z web-0 nginx: 10.0.0.2 - - [15/Jan/2024:10:05:01 +0000] "GET /health HTTP/1.1" 200 2
```

## SDL Endpoints

### Validate SDL

Validate SDL syntax without creating deployment.

```http
POST /sdl/validate
```

**Request Body:**
```json
{
  "sdl": "<sdl-string>"
}
```

**Response (valid):**
```json
{
  "success": true,
  "data": {
    "valid": true,
    "version": "2.0",
    "services": ["web"],
    "profiles": ["web"],
    "placements": ["dcloud"]
  }
}
```

**Response (invalid):**
```json
{
  "success": false,
  "error": {
    "code": "INVALID_SDL",
    "message": "Invalid SDL",
    "details": [
      {
        "path": "services.web.image",
        "message": "Image tag 'latest' is not allowed"
      }
    ]
  }
}
```

### Estimate Price

Get price estimate for SDL.

```http
POST /sdl/price
```

**Request Body:**
```json
{
  "sdl": "<sdl-string>"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "estimatedMonthlyUakt": "438000000",
    "estimatedMonthlyUsd": "50.00",
    "resources": {
      "cpu": 0.5,
      "memory": "512Mi",
      "storage": "1Gi"
    }
  }
}
```

## Provider Endpoints

### List Providers

Get available providers.

```http
GET /providers
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `region` | string | Filter by region |
| `hasGpu` | boolean | Filter GPU providers |
| `active` | boolean | Only active providers |

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "address": "akash1prov...",
      "hostUri": "https://provider.example.com",
      "attributes": {
        "region": "us-west",
        "host": "provider1"
      },
      "status": {
        "cluster": {
          "availableResources": {
            "cpu": 100,
            "memory": "200Gi",
            "storage": "1Ti"
          }
        }
      }
    }
  ]
}
```

## Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `UNAUTHORIZED` | 401 | Invalid or missing authentication |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `INVALID_SDL` | 400 | SDL validation failed |
| `INVALID_REQUEST` | 400 | Malformed request |
| `INSUFFICIENT_BALANCE` | 400 | Wallet balance too low |
| `DEPLOYMENT_NOT_FOUND` | 404 | Deployment doesn't exist |
| `LEASE_NOT_FOUND` | 404 | Lease doesn't exist |
| `PROVIDER_OFFLINE` | 503 | Provider unavailable |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |
