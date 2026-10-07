# Console Account & Funding

A Console account *is* a managed wallet. The API key authenticates as the account, and deployments spend from the account's credits automatically. There is no separate wallet to enable and nothing to fund per deployment.

## The model

```
Console account
├── login (email + password, or OAuth)
├── managed wallet: signs every deployment action
│   └── credits (USD), split into
│       ├── Available: free to fund new and running deployments
│       └── Escrow: held by running deployments, returned as each one closes
└── API keys: each one acts as the whole account
```

Each deployment still has its own escrow account on Akash; Console fills it for you. The Console UI shows the split as **Available** and **Escrow**, the same words the API uses.

## Setup happens in the UI

None of these steps has a supported API:

1. **Sign up** at [console.akash.network](https://console.akash.network) and verify the email address. New accounts may start on a free trial with a small credit and some limits (certain GPU models, a restricted provider list); a trial account may have to accept the Fair Use Policy in the UI before its first deploy (`403 fair_use_policy_required` otherwise).
2. **Add credits** under **Billing**, by card through Stripe.
3. **Optionally turn on Auto recharge** under Billing, so the card is charged before credits run out.
4. **Create an API key** under **Settings → API Keys** (**@authentication.md**).

## Reading the balance

```bash
curl -s https://console-api.akash.network/v1/balances -H "x-api-key: $AKASH_API_KEY" | jq .data
```

```json
{ "balance": 42.17, "deployments": 6.3, "total": 48.47 }
```

All values are USD. `balance` is **Available**, `deployments` is the **Escrow** held by running deployments (not spent: it returns to `balance` as they close), and `total` is the sum. With the API key and no query string, the call reads your own account; `?address=akash1...` reads any address without a key.

Related reads:

| Endpoint | Returns |
|---|---|
| `GET /v1/weekly-cost` | USD per week across your running deployments |
| `GET /v1/usage/history?address=&startDate=&endDate=` | Daily spend for an address (public; at most 366 days). Your wallet address is the `owner` of any of your deployments (`deployment.id.owner`). |
| `GET /v1/deployment-funding-config` | The constants automatic funding runs on (below) |

## How automatic funding works

Console funds every deployment from the account's credits; there is no deposit to send and no top-up to call. `GET /v1/deployment-funding-config` (public) returns the constants:

```json
{ "data": { "targetRunwayHours": 48, "balanceHeadroomUsd": 5, "defaultDepositUsd": 0.5 } }
```

- Each deployment starts with `defaultDepositUsd` in escrow. Creating one with less available answers **402 `insufficient_balance`**.
- Once its lease starts, Console tops the escrow up toward `targetRunwayHours` of runtime and keeps it there while credits last.
- Top-ups leave about `balanceHeadroomUsd` of the available balance untouched, so a new deployment can still be created.
- When the credits run out, running deployments live on what their escrow holds, up to about `targetRunwayHours`, then close. Adding credits is the fix; it is a UI action.

The one programmatic knob is a deployment's **runtime limit**, which closes it after a set number of hours: `runtimeLimitHours` on create, or `PATCH /v2/deployment-settings/{dseq}` (**@deployment-endpoints.md**). Don't call `POST /v1/deposit-deployment`: it is deprecated and does nothing automatic funding doesn't already do.

## When a create is refused for money

| Response | Meaning | Do this |
|---|---|---|
| 402 `insufficient_balance` | Available credit is below what the new deployment needs. `data.requiredAmountUsd` and `data.availableAmountUsd` give the gap. | Tell the user to add credits in the Console UI, or close deployments they no longer need |
| 402 `balance_top_up_pending` | Auto recharge is already charging the card | Retry after the `Retry-After` header |
| 402 `payment_required` | The fee allowance ran out, or a trial account asked for something the trial excludes | Add credits |

## Not programmatic

These are Console UI features, and the endpoints behind them are internal (listed in **@overview.md**):

- Signup, login, email verification, account deletion
- Payment methods, adding credits, invoices and billing history
- Auto recharge settings
- Profile, favorites, saved templates, alerts and notification channels
- **Signing arbitrary transactions.** The managed wallet's key can't be exported, and no endpoint signs a message of your choosing; `/v1/tx` is the Console UI's legacy signer and accepts only six message types (deployment, lease, deposit and certificate messages). Use the dedicated endpoints, and switch to a self-custody SDK for anything they don't cover.
- **Self-custody wallets.** Keplr and Ledger never touch the Console API; they use the CLI or an SDK (`../cli/`, `../../sdk/`).

## Related files

- **@authentication.md** — API keys
- **@deployment-endpoints.md** — Deployments, leases, bids, runtime limits
- **@api-key-quickstart.md** — End-to-end walkthrough
