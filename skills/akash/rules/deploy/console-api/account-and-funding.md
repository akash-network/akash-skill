# Console Account & Funding

Console holds the wallet. A Console user has a personal account and can belong to teams, and each of them has its own managed wallet and credits. An API key acts in the one it was created in, and deployments spend from that wallet's credits automatically. There is no separate wallet to enable and nothing to fund per deployment.

## The model

```
Console user
├── login (email + password, or OAuth)
├── personal account                     (type "personal"; the user is its only member)
│   ├── managed wallet: signs every deployment action
│   │   └── credits (USD), split into
│   │       ├── Available: free to fund new and running deployments
│   │       └── Escrow: held by running deployments, returned as each one closes
│   ├── projects: a default one, plus any others
│   └── API keys: act here only, optionally limited to one project
└── teams the user belongs to, each with
    ├── its own managed wallet, credits, cards and Auto recharge
    ├── projects, starting with a default one
    ├── members with roles (owner, admin, member, billing, viewer)
    └── the user's API keys for this team: act here only, with the user's role, optionally limited to one project
```

Each deployment still has its own escrow account on Akash; Console fills it for you. The Console UI shows the split as **Available** and **Escrow**, the same words the API uses. Teams, projects and roles: **@teams-and-projects.md**.

## Setup happens in the UI

None of these steps has a supported API:

1. **Sign up** at [console.akash.network](https://console.akash.network) and verify the email address. New accounts may start on a free trial with a small credit and some limits (certain GPU models, a restricted provider list); a trial account may have to accept the Fair Use Policy in the UI before its first deploy (`403 fair_use_policy_required` otherwise).
2. **Add credits** under **Billing**, by card through Stripe.
3. **Optionally turn on Auto recharge** under Billing, so the card is charged before credits run out.
4. **Create an API key** under **Settings → API Keys** (**@authentication.md**).

A team does the same on its own **Billing** page, separately from any member's personal account. Only its owners and billing members add credits, manage cards and set Auto recharge. Teams never get a free trial, so a new team can't deploy until someone adds credits.

## Reading the balance

```bash
curl -s https://console-api.akash.network/v1/balances -H "x-api-key: $AKASH_API_KEY" | jq .data
```

```json
{ "balance": 42.17, "deployments": 6.3, "total": 48.47 }
```

All values are USD. `balance` is **Available**, `deployments` is the **Escrow** held by running deployments (not spent: it returns to `balance` as they close), and `total` is the sum. With the API key and no query string, the call reads the wallet the key acts in: its creator's personal account, or its team's wallet for a team key, which every member shares. `?address=akash1...` reads any address without a key.

Related reads:

| Endpoint | Returns |
|---|---|
| `GET /v1/weekly-cost` | USD per week across the running deployments of the key's account or team |
| `GET /v1/usage/history?address=&startDate=&endDate=` | Daily spend for an address (public; at most 366 days). The wallet address is the `owner` of any deployment it pays for (`deployment.id.owner`); a team deployment's owner is the team wallet. |
| `GET /v1/project-spend`, `GET /v1/deployment-spend` | A team's spend per project, and per deployment and day (**@teams-and-projects.md**) |
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
| 402 `insufficient_balance` | Available credit is below what the new deployment needs. `data.requiredAmountUsd` and `data.availableAmountUsd` give the gap. | Tell the user to add credits in the Console UI, or close deployments they no longer need. For a team key, the team's credits are short: an owner or billing member adds them on the team's Billing page. |
| 402 `balance_top_up_pending` | Auto recharge is already charging the card | Retry after the `Retry-After` header |
| 402 `payment_required` | The fee allowance ran out, or a trial account asked for something the trial excludes | Add credits |
| 403 `project_budget_exceeded` | The project's monthly budget is spent | An owner or admin raises it (**@teams-and-projects.md**); retrying won't help |

Credits never move between a personal account and a team, and a key can't switch to another one's wallet.

## Not programmatic

These are Console UI features, and the endpoints behind them are internal (listed in **@overview.md**):

- Signup, login, email verification, account deletion
- Creating a team and accepting an invitation (a Console session only; an API key gets 403 `session_required`)
- Payment methods, adding credits, invoices and billing history, for a personal account or a team
- Auto recharge settings
- Profile, favorites, saved templates, alerts and notification channels
- **Signing arbitrary transactions.** The managed wallet's key can't be exported, and no endpoint signs a message of your choosing; `/v1/tx` is the Console UI's legacy signer and accepts only six message types (deployment, lease, deposit and certificate messages). Use the dedicated endpoints, and switch to a self-custody SDK for anything they don't cover.
- **Self-custody wallets.** Keplr and Ledger never touch the Console API; they use the CLI or an SDK (`../cli/`, `../../sdk/`).

## Related files

- **@authentication.md** — API keys
- **@deployment-endpoints.md** — Deployments, leases, bids, runtime limits
- **@api-key-quickstart.md** — End-to-end walkthrough
- **@teams-and-projects.md**: Teams, projects, roles and team billing
