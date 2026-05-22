# Console Account & Funding

When you sign up on console.akash.network, your account *is* a managed wallet. There isn't a separate "wallet" product to enable — the API key authenticates as your account, and deployments spend from that account's wallet automatically.

This file covers the lifecycle around the account: how to bootstrap one (UI-only) and how to read account state programmatically. All wallet operations — signing transactions, depositing to deployments — happen through the dedicated deployment endpoints in **@deployment-endpoints.md**, not through any account-level "send arbitrary tx" endpoint (no such programmatic endpoint exists in the documented API).

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

> ⚠️ **Swagger-only (Tier 2).** Not in the [official API reference](https://akash.network/docs/api-documentation/console-api/api-reference/) — observed on the live service but may change without notice. Pin to a tested runtime version.

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

### Auto-top-up (per-deployment)

Programmatic auto-top-up is supported, but only per-deployment via the **v2** endpoints — see **@deployment-endpoints.md** § "Auto-top-up (deployment settings v2)". Global account-level auto-reload (`/v1/wallet-settings`) is UI-only.

## What this file deliberately does NOT cover

The following are real Console-UI features but are **not** part of the documented programmatic API. Use the UI for these; don't write code against the underlying endpoints.

- **Account creation, password reset, email verification, OAuth flows** — UI only.
- **Stripe payment methods, payment confirmation, transaction history, customer management** — UI only. All `/v1/stripe/*` endpoints back the Console's billing screens.
- **Account-level auto-reload** (`/v1/wallet-settings`) — UI only. (Per-deployment auto-top-up via `/v2/deployment-settings/*` *is* documented as programmatic — covered in `deployment-endpoints.md`.)
- **Username and profile management** (`/v1/user/*`) — UI only.
- **Favorite templates, saved templates, newsletter signup** — UI only.
- **Alerts and notification channels** — UI only.
- **Console dashboard analytics** (`/v1/bme/*`, `/v1/dashboard-data`, etc.) — UI only.
- **Arbitrary signed transactions.** The Console API documentation explicitly states "you cannot export private keys or sign arbitrary transactions." There is no documented endpoint to broadcast a custom `Msg*` from the managed wallet — use the dedicated deployment endpoints, and if you need a chain message they don't cover, switch to a self-custody SDK.
- **Self-custody wallets.** Keplr or Ledger don't touch the Console API at all. Use the CLI or an SDK (see `../cli/` and `../../sdk/`).

## Related files

- **@authentication.md** — `x-api-key` setup
- **@deployment-endpoints.md** — Full endpoint reference (Deployments, Leases, Bids, Auto-top-up)
- **@api-key-quickstart.md** — End-to-end walkthrough
