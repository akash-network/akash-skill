# Deployment Methods Overview

Choose the right deployment method for your use case.

## Comparison

| Method | Best For | Complexity | Automation |
|--------|----------|------------|------------|
| **Console UI** | Manual deployments, learning | Low | None |
| **Console API** | Automated deployments, integrations | Medium | High |
| **CLI** | DevOps, scripting, power users | Medium | Medium |
| **TypeScript SDK** | Web apps, Node.js services | Medium | High |
| **Go SDK** | Backend services, custom tooling | High | High |

## Console UI

The [Akash Console](https://console.akash.network) web interface.

**Pros:**
- No setup required
- Visual deployment wizard
- Easy provider selection
- Built-in SDL editor

**Cons:**
- Manual process
- Not automatable
- Requires browser

**Best for:** Learning Akash, one-off deployments, exploring providers.

## Console API

REST API at `https://console-api.akash.network/v1`.

**Pros:**
- Programmatic deployments
- Managed wallet support
- No certificate management
- Simple REST calls

**Cons:**
- Depends on Console service
- API key required
- Rate limits apply

**Best for:** Automated deployments, CI/CD integration, managed wallet users.

See **@deploy/console-api/** for complete documentation.

## Akash CLI

Command-line interface using `akash` binary.

**Pros:**
- Full control
- Scriptable
- Works offline (with node)
- No third-party dependencies

**Cons:**
- Requires setup
- Certificate management
- Key management

**Best for:** DevOps workflows, scripting, advanced users.

See **@deploy/cli/** for complete documentation.

## TypeScript SDK

`@akashnetwork/akashjs` package for Node.js and browsers.

**Pros:**
- Native JS/TS integration
- Works in browsers
- Type safety
- Chain and provider SDKs

**Cons:**
- Requires SDK knowledge
- More code to write

**Best for:** Web applications, Node.js services, dApps.

See **@sdk/typescript/** for complete documentation.

## Go SDK

Go packages for Akash integration.

**Pros:**
- High performance
- Native blockchain integration
- Full feature access

**Cons:**
- Go knowledge required
- More complex setup

**Best for:** Backend services, custom providers, tooling.

See **@sdk/go/** for complete documentation.

## Decision Flowchart

```
Start
  │
  ├── Need automation? ──No──► Console UI
  │         │
  │        Yes
  │         │
  ├── Using managed wallet? ──Yes──► Console API
  │         │
  │        No
  │         │
  ├── Building web app? ──Yes──► TypeScript SDK
  │         │
  │        No
  │         │
  ├── Building Go service? ──Yes──► Go SDK
  │         │
  │        No
  │         │
  └── CLI (default for scripting)
```

## Quick Start by Method

### Console UI

1. Visit https://console.akash.network
2. Connect wallet (Keplr, Leap)
3. Click "Deploy"
4. Select template or paste SDL
5. Choose provider
6. Deploy

### Console API

```bash
# Create deployment with managed wallet
curl -X POST https://console-api.akash.network/v1/deployment \
  -H "Authorization: Bearer <api-key>" \
  -H "Content-Type: application/json" \
  -d '{"sdl": "..."}'
```

### CLI

```bash
# Install
curl -sSfL https://get.akash.network | sh

# Create deployment
akash tx deployment create deploy.yaml --from wallet

# Accept bid
akash tx market lease create --dseq <dseq> --provider <provider> --from wallet
```

### TypeScript SDK

```typescript
import { deploymentCreate } from "@akashnetwork/akashjs/build/stargate";

const tx = await deploymentCreate(client, {
  owner: address,
  sdl: parsedSdl,
  deposit: { denom: "uact", amount: "5000000" }
});
```

## Authentication Methods

| Method | Console API | CLI | SDK |
|--------|-------------|-----|-----|
| API Key | Yes | No | No |
| Wallet Key | Via managed wallet | Yes | Yes |
| JWT Token | Yes | No | Yes |
| mTLS Certificate | No | Yes (legacy) | Yes (legacy) |

## Recommended Approach

| Scenario | Recommended Method |
|----------|-------------------|
| Learning Akash | Console UI |
| Production automation | Console API or TypeScript SDK |
| CI/CD pipeline | CLI or Console API |
| Custom deployment platform | TypeScript SDK |
| Backend service integration | Go SDK |
| Quick scripting | CLI |

## Migration Between Methods

All methods work with the same:
- SDL format
- Blockchain state
- Providers

You can start with Console UI and migrate to API/SDK later without changing your SDL files.
