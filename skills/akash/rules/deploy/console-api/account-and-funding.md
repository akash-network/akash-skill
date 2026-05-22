# Console Account & Funding

When you sign up on console.akash.network, your account *is* a managed wallet. There isn't a separate "wallet" product to enable — the API key authenticates as your account, and deployments spend from that account's wallet automatically.

This file covers the lifecycle around the account: how to bootstrap one (UI-only), reading balances programmatically, funding with Stripe, and the `/v1/tx` escape hatch for arbitrary signed messages.

## The model

```
Console account
├── email + password (or OAuth)
├── managed wallet (the on-chain address that signs your deployments)
│   ├── balance (denominated in USD internally; uact on-chain)
│   └── auto-top-up settings
└── API keys (one or more — each authenticates as this account)
```

The API key doesn't carry a wallet of its own. It's an authentication credential that authorizes operations on the account, and the account is what holds the wallet.

## Account lifecycle

### Sign up — use the Console UI, not the API

Account creation is a **UI-only flow**. Go to [console.akash.network](https://console.akash.network), sign up with email + password (or OAuth), and verify your email via the link in your inbox. The Console handles email verification end-to-end through the UI.

> Do not call `POST /v1/auth/signup`, `POST /v1/send-verification-email`, or `POST /v1/verify-email` from your application. These endpoints back the Console UI; they are not part of the supported programmatic surface and may change without notice. Direct users to the Console UI for any account creation, password reset, or email verification action.

Once your account is verified, the rest of this file applies — you'll have an account with a managed wallet attached, and you can read its state via the API.

### Generate an API key — also via the UI

API keys are generated through **Settings → API Keys** in the Console UI. The plaintext key is shown once at creation; copy it then. Programmatic API-key management endpoints (`/v1/api-keys`) exist for rotating or listing existing keys — see **@authentication.md** — but the **first** key has to be created through the UI because you don't have a key to authenticate to the API yet.

Bootstrap order:
1. Sign up in the Console UI.
2. Verify email via the UI / your inbox.
3. Fund the wallet (Settings → Payment Methods → add a card).
4. Generate an API key in the UI (copy it once, store it as `AKASH_API_KEY`).
5. *Then* — and only then — use the programmatic endpoints below.

### Get your user / me

```
GET /v1/user/me
```

**Auth:** `x-api-key` or `Authorization: Bearer <jwt>`

Returns your account record including username, email verification state, and account metadata.

## Funding the account

### Read your balance

```
GET /v1/balances?address=<your-akash-address>
```

**Auth:** Public (the endpoint is gated on knowing the address, which is public anyway)

**Response:**
```json
{
  "data": {
    "balance": <usd-number>,
    "deployments": <usd-spent-on-active-deployments>,
    "total": <usd-number>
  }
}
```

All values are USD numbers. The conversion from `uact` happens server-side.

You can find your address via `GET /v1/user/me`.

### Add a payment method (Stripe)

The Console funds the managed wallet via Stripe. There's a small set of endpoints to manage cards:

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/v1/stripe/payment-methods/setup` | Begin a Stripe SetupIntent for a new card |
| `POST` | `/v1/stripe/payment-methods/validate` | Validate the card after SetupIntent confirmation |
| `GET` | `/v1/stripe/payment-methods` | List your cards |
| `POST` | `/v1/stripe/payment-methods` | Attach a card to your account |
| `GET` | `/v1/stripe/payment-methods/default` | Read the default card |
| `POST` | `/v1/stripe/payment-methods/default` | Set the default card |
| `DELETE` | `/v1/stripe/payment-methods/{paymentMethodId}` | Remove a card |

All require `x-api-key`.

For most flows this is done through the Console UI — programmatic card management is not the common path. Use the UI to add a card, then deploy from the API.

### Trigger a charge

```
POST /v1/stripe/transactions/confirm
```

**Auth:** `x-api-key`

Confirms a pending Stripe transaction (e.g. an account top-up) using your default payment method.

```
GET /v1/stripe/transactions
GET /v1/stripe/transactions/export
```

List and export your transaction history.

### Auto-top-up

```
GET    /v1/wallet-settings
POST   /v1/wallet-settings
PUT    /v1/wallet-settings
DELETE /v1/wallet-settings
```

**Auth:** `x-api-key`

Single resource per account. Body:

```json
{ "data": { "autoReloadEnabled": true } }
```

Per-deployment overrides:

```
POST  /v1/deployment-settings
GET   /v1/deployment-settings/{userId}/{dseq}
PATCH /v1/deployment-settings/{userId}/{dseq}
```

— or the newer v2 path (drops `userId`, inferred from auth):

```
POST  /v2/deployment-settings
GET   /v2/deployment-settings/{dseq}
PATCH /v2/deployment-settings/{dseq}
```

The v2 response includes `estimatedTopUpAmount` and `topUpFrequencyMs`. Body:

```json
{ "data": { "dseq": "12345678", "autoTopUpEnabled": true } }
```

## Wallet introspection

### List your managed wallets

```
GET /v1/wallets?userId=<your-user-id>
```

**Auth:** `x-api-key`

Returns the wallet objects associated with your account:

```json
{
  "data": [
    {
      "id": "...",
      "userId": "...",
      "address": "akash1...",
      "denom": "uact",
      "creditAmount": <usd-number>,
      "isTrialing": false,
      "requires3DS": false,
      "clientSecret": "..."
    }
  ]
}
```

Most accounts have exactly one wallet. Multi-wallet accounts are rare and handled the same way.

### Trial wallet (UI-only onboarding endpoint)

`POST /v1/start-trial` backs a step of the Console UI's onboarding flow. **Do not call it from your application** — like signup and email verification, it's part of the UI's internal surface, not a supported programmatic endpoint. Documented here only so the model recognizes it if it appears in logs or browser dev tools.

## Generic signed transaction

```
POST /v1/tx
```

**Auth:** `x-api-key`

The escape hatch. Broadcasts an arbitrary Akash chain message signed by your account's managed wallet. Use this when there's no purpose-built endpoint for what you want to do.

**Body:**
```json
{
  "data": {
    "userId": "<your-user-id>",
    "messages": [
      {
        "typeUrl": "/akash.deployment.v1beta4.MsgCloseDeployment",
        "value": { "id": { "owner": "akash1...", "dseq": "12345678" } }
      }
    ]
  }
}
```

See `deployment-endpoints.md` for the full list of allowed `typeUrl` values and which dedicated endpoint to prefer when one exists.

## What this file does NOT cover

- **Self-custody wallets.** Keplr or Ledger — none of those touch the Console API. Use the CLI or an SDK (see `../cli/` and `../../sdk/`).
- **Direct on-chain transactions.** If you want to construct and broadcast `MsgCreateDeployment` yourself, use the Go or TypeScript SDK — the Console API's `/v1/tx` will sign with the *managed* wallet, not yours.

## Related files

- **@authentication.md** — `x-api-key` setup, API Keys CRUD, JWT minting
- **@deployment-endpoints.md** — Full endpoint reference (Deployments, Leases, Bids, Pricing, `/v1/tx` allowed typeUrls)
- **@api-key-quickstart.md** — End-to-end walkthrough
- **@operations.md** — Logs, events, status, shell (post-deploy)
