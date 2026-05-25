# JWT Authentication

JWT-based authentication for Akash deployments and provider communication.

## Overview

JWT (JSON Web Token) authentication is the modern method for authenticating with Akash providers and the Console API.

## How JWT Auth Works

```
1. Client signs a message with wallet private key
2. Server verifies signature against on-chain public key
3. Server issues JWT token
4. Client uses JWT for subsequent requests
```

## Obtaining JWT Token

### Via Console API

```bash
# Request challenge
curl -X POST https://console-api.akash.network/v1/auth/challenge \
  -H "Content-Type: application/json" \
  -d '{"address": "akash1..."}'

# Response
{
  "challenge": "Sign this message to authenticate: abc123..."
}
```

### Sign Challenge (Browser/Keplr)

```typescript
async function getJwtToken(address: string): Promise<string> {
  // 1. Request challenge
  const challengeRes = await fetch('https://console-api.akash.network/v1/auth/challenge', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ address })
  });
  const { challenge } = await challengeRes.json();

  // 2. Sign with wallet
  const signature = await window.keplr!.signArbitrary(
    'akashnet-2',
    address,
    challenge
  );

  // 3. Exchange for JWT
  const tokenRes = await fetch('https://console-api.akash.network/v1/auth/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      address,
      challenge,
      signature: signature.signature,
      pubKey: signature.pub_key
    })
  });

  const { token } = await tokenRes.json();
  return token;
}
```

### Sign Challenge (CLI)

```bash
# Sign message
akash tx auth sign-msg "challenge-string" --from wallet

# Use returned signature to get JWT
```

## Using JWT

### API Requests

```bash
curl https://console-api.akash.network/v1/deployment \
  -H "Authorization: Bearer <jwt-token>"
```

### TypeScript

```typescript
const headers = {
  'Authorization': `Bearer ${jwtToken}`,
  'Content-Type': 'application/json'
};

const response = await fetch('https://console-api.akash.network/v1/deployment', {
  headers
});
```

## Token Lifecycle

| Property | Value |
|----------|-------|
| Expiration | Typically 24 hours |
| Refresh | Re-authenticate before expiry |
| Revocation | Not supported (wait for expiry) |
| Storage | Secure memory or httpOnly cookie |

## Security Best Practices

1. **Store tokens securely** - Use httpOnly cookies in browsers
2. **Never log tokens** - Avoid console.log or server logs
3. **Handle expiration** - Implement refresh logic
4. **Use HTTPS only** - Never send tokens over HTTP
5. **Minimal scope** - Request minimum permissions needed
