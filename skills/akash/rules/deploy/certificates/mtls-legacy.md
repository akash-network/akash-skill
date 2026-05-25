# mTLS Authentication (Legacy)

Mutual TLS certificate-based authentication for Akash provider communication.

> **Console API users: this is not for you.**
>
> `POST /v1/certificates` on the Console API now returns **400 Bad Request** with the message:
> *"This endpoint has been removed. mTLS certificates are no longer required as identity is now verified via API key."*
>
> If you are on the Console API path, do **not** create certificates. Authentication is `x-api-key` for the Console API calls, and a JWT minted via `POST /v1/create-jwt-token` for direct calls to the provider (logs, events, status, shell). See **@../console-api/authentication.md** and **@../console-api/operations.md**.
>
> The remainder of this file documents the **CLI path**, where mTLS is still used for self-custody clients calling providers directly (e.g. `akash provider lease-status`, `akash provider lease-logs`). AEP-64 JWT auth is gradually replacing mTLS even on the CLI path; new code should prefer JWT.

## Overview

mTLS (Mutual TLS) was the original authentication method for Akash provider communication. JWT authentication ([AEP-64](https://akash.network/roadmap/aep-64/)) is now preferred everywhere, and mTLS is being phased out. The Console API has already removed it; the CLI keeps it as a fallback for now.

## How mTLS Works

```
1. Client generates X.509 certificate
2. Client broadcasts certificate to blockchain
3. Provider verifies certificate against on-chain record
4. Both client and provider authenticate each other
```

## Certificate Creation

### CLI

```bash
# Generate and broadcast certificate
akash tx cert create client --from wallet
```

This generates:
- Client certificate (public)
- Client private key (kept local)
- Broadcasts certificate hash to blockchain

### TypeScript SDK

```typescript
import { certificateManager } from "@akashnetwork/chain-sdk";

// Generate certificate (legacy — prefer JwtTokenManager for new code)
const cert = await certificateManager.createCertificate(address);

// cert contains:
// - cert: X.509 certificate (PEM)
// - privateKey: Private key (PEM)
// - publicKey: Public key (PEM)
```

### Broadcast Certificate

Use the SDK proxy for the chain message. The cert module is at `akash.cert.v1`:

```typescript
// Via the SDK proxy:
await sdk.akash.cert.v1.createCertificate({
  cert: certPem,
  pubkey: pubKeyPem,
  // signed transaction handled by the SDK
});

// Or build the raw message manually from private-types:
import { MsgCreateCertificate } from "@akashnetwork/chain-sdk/private-types/akash.v1";

const msg = {
  typeUrl: "/akash.cert.v1beta3.MsgCreateCertificate",
  value: {
    owner: address,
    cert: Buffer.from(cert.cert).toString("base64"),
    pubkey: Buffer.from(cert.publicKey).toString("base64")
  }
};

await client.signAndBroadcast(address, [msg], "auto");
```

## Certificate Storage

### CLI

Certificates stored in `~/.akash/` directory.

### Application

Store securely:

```typescript
// Save to secure storage
const certData = {
  cert: cert.cert,
  privateKey: cert.privateKey,
  publicKey: cert.publicKey,
  address: address,
  createdAt: new Date().toISOString()
};

// Encrypt before persisting
```

## Using Certificates

### Provider Communication

```typescript
import https from "https";

const agent = new https.Agent({
  cert: certPem,
  key: privateKeyPem,
  rejectUnauthorized: false  // Provider uses self-signed certs
});

const response = await fetch(providerUrl, {
  agent,
  method: "PUT",
  body: JSON.stringify(manifest)
});
```

### CLI Provider Operations

Certificate is used automatically:

```bash
akash provider send-manifest deploy.yaml \
  --dseq <DSEQ> \
  --provider <PROVIDER> \
  --from wallet
```

## Certificate Lifecycle

| Operation | Command |
|-----------|---------|
| Create | `akash tx cert create client --from wallet` |
| Query | `akash query cert list --owner <address>` |
| Revoke | `akash tx cert revoke --from wallet` |

### Certificate States

```
Active → Revoked
```

Only one active certificate per address.

### Renewing Certificates

```bash
# Revoke old
akash tx cert revoke --from wallet

# Create new
akash tx cert create client --from wallet
```

## Query Certificates

### CLI

```bash
akash query cert list --owner $(akash keys show wallet -a)
```

### REST API

```bash
curl "https://api.akashnet.net/akash/cert/v1beta3/certificates/list?filter.owner=akash1..."
```

## Troubleshooting

### Certificate Mismatch

```
Error: certificate verification failed
```

**Cause:** Local certificate doesn't match on-chain record.

**Solution:** Revoke and recreate certificate.

### Expired Certificate

```
Error: certificate expired
```

**Solution:** Revoke old certificate and create new one.

### Provider Rejection

```
Error: provider rejected manifest
```

**Cause:** Certificate issue or manifest mismatch.

**Solution:**
1. Verify certificate is active on-chain
2. Check manifest matches deployment

## Migration to JWT

For new integrations, prefer JWT authentication:

- Simpler setup (no certificate management)
- Works with Console API
- Better for web applications
- No on-chain certificate needed

See **@jwt-auth.md** for JWT setup.

## When to Use mTLS

| Scenario | Recommended |
|----------|-------------|
| New projects | JWT |
| CLI usage | mTLS (automatic) |
| Existing integrations | mTLS (continue) |
| Web applications | JWT |
| Provider development | mTLS |
