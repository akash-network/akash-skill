# Console Account & Funding

When you sign up on console.akash.network, your account *is* a managed wallet. There isn't a separate "wallet" product to enable — the API key authenticates as your account, and deployments spend from that account's wallet automatically.

This file covers the lifecycle around the account: how to bootstrap one (UI-only), how to read your balance programmatically, and the `/v1/tx` escape hatch for arbitrary signed messages.

## The model

```
Console account
├── email + password (or OAuth)
├── managed wallet (the on-chain address that signs your deployments)
│   ├── balance (denominated in USD internally; uact on-chain)
│   └── auto-top-up settings (managed in the UI)
└── API keys (one or more — each authenticates as this account)
```

The API key doesn't carry a wallet of its own. It's an authentication credential that authorizes operations on the account, and the account is what holds the wallet.

## Bootstrap order (UI for setup, API for runtime)

The following steps are **UI-only** at [console.akash.network](https://console.akash.network) — there is no programmatic API for any of them, and the underlying endpoints (`/v1/auth/signup`, `/v1/send-verification-email`, `/v1/verify-email`, `/v1/start-trial`, all `/v1/stripe/*` payment endpoints, `/v1/wallet-settings`, `/v1/deployment-settings`, `/v1/user/*` profile endpoints) are not part of the supported programmatic surface and may change without notice.

1. **Sign up** in the Console UI (email + password, or OAuth).
2. **Verify email** via the link sent to your inbox.
3. **Add a payment method** in Settings → Payment Methods (Stripe).
4. **Fund the wallet** — top up via the UI; the credit balance becomes spendable as ACT.
5. **(Optional) Enable auto-top-up** in Settings if you don't want to manually reload before deployments stall.
6. **Generate an API key** in Settings → API Keys. Plaintext is shown once at creation; copy it and store as `AKASH_API_KEY`.

Only after step 6 do you have an API key to authenticate the programmatic endpoints below.

## Programmatic surface — reading balance and signing transactions

These are the only two account-related operations supported via the API. Everything else listed above is UI-only.

### Read your balance

```
GET /v1/balances?address=<your-akash-address>
```

**Auth:** Public (the endpoint is gated on knowing the address, which is public anyway).

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

Your account's wallet address is shown in the Console UI under Settings; copy it once and store it alongside your API key (e.g., `AKASH_WALLET_ADDRESS`).

### Generic signed transaction

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

See **@deployment-endpoints.md** for the full list of allowed `typeUrl` values and which dedicated endpoint to prefer when one exists. Most workflows don't need `/v1/tx` — reach for it only when you need a chain message that isn't exposed via a dedicated endpoint.

## What this file deliberately does NOT cover

The following are real Console-UI features but are **not** part of the programmatic API contract. Use the UI for these; don't write code against the underlying endpoints.

- **Account creation, password reset, email verification, OAuth flows** — UI only.
- **Stripe payment methods, payment confirmation, transaction history, customer management** — UI only. All `/v1/stripe/*` endpoints back the Console's billing screens; they are not for programmatic use.
- **Auto-top-up configuration** (`/v1/wallet-settings`, `/v1/deployment-settings/*`, `/v2/deployment-settings/*`) — UI only (Settings → Auto-top-up; per-deployment toggles on each deployment page).
- **Username and profile management** (`/v1/user/*`) — UI only.
- **Favorite templates, saved templates, newsletter signup** — UI only.
- **Alerts and notification channels** — UI only.
- **Console dashboard analytics** (`/v1/bme/*`, `/v1/dashboard-data`, etc.) — UI only.
- **Self-custody wallets.** Keplr or Ledger don't touch the Console API at all. Use the CLI or an SDK (see `../cli/` and `../../sdk/`).
- **Direct on-chain transactions from a non-Console wallet.** `/v1/tx` signs with the *managed* wallet on your Console account. If you want to broadcast from your own self-custody wallet, use the Go or TypeScript SDK.

## Related files

- **@authentication.md** — `x-api-key` setup, JWT minting, API Keys CRUD (for rotating keys after the first one is generated in the UI)
- **@deployment-endpoints.md** — Full endpoint reference (Deployments, Leases, Bids, Pricing, `/v1/tx` allowed typeUrls)
- **@api-key-quickstart.md** — End-to-end walkthrough
- **@operations.md** — Logs, events, status, shell (post-deploy)
