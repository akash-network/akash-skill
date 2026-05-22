# AuthZ Overview

Akash supports Cosmos SDK AuthZ (authorization) for delegated permissions, allowing one account to perform actions on behalf of another.

## What is AuthZ?

AuthZ allows a **granter** to authorize a **grantee** to execute specific message types. This enables:

- Deployment automation without exposing main wallet
- Fee grants for sponsored deployments
- Delegated deployment management
- Multi-tenant deployment platforms

## Use Cases

| Use Case | Granter | Grantee | Permission |
|----------|---------|---------|------------|
| Automation bot | User wallet | Bot wallet | CreateDeployment, CloseDeployment |
| Fee sponsorship | Sponsor | User | Pay fees on behalf |
| Platform | User | Platform wallet | Manage deployments |
| Team access | Org wallet | Team member | Deployment management |

## Grant Types

### Deployment Grants

Allow creating and managing deployments:

```bash
# Grant deployment creation
akash tx authz grant <GRANTEE_ADDRESS> generic \
  --msg-type /akash.deployment.v1beta3.MsgCreateDeployment \
  --from granter

# Grant deployment closure
akash tx authz grant <GRANTEE_ADDRESS> generic \
  --msg-type /akash.deployment.v1beta3.MsgCloseDeployment \
  --from granter

# Grant deposit
akash tx authz grant <GRANTEE_ADDRESS> generic \
  --msg-type /akash.deployment.v1beta3.MsgDepositDeployment \
  --from granter
```

### Market Grants

Allow lease operations:

```bash
# Grant lease creation
akash tx authz grant <GRANTEE_ADDRESS> generic \
  --msg-type /akash.market.v1beta4.MsgCreateLease \
  --from granter
```

### Fee Grants

Allow one account to pay fees for another:

```bash
# Basic fee grant
akash tx feegrant grant <GRANTER_ADDRESS> <GRANTEE_ADDRESS> \
  --from granter

# With spending limit
akash tx feegrant grant <GRANTER_ADDRESS> <GRANTEE_ADDRESS> \
  --spend-limit 10000000uakt \
  --from granter

# With expiration
akash tx feegrant grant <GRANTER_ADDRESS> <GRANTEE_ADDRESS> \
  --expiration "2025-12-31T23:59:59Z" \
  --from granter
```

## How It Works

```
┌──────────┐                    ┌──────────┐
│ Granter  │ ─── Grant Auth ──► │  Chain   │
│ (Owner)  │                    │          │
└──────────┘                    └──────────┘
                                     │
┌──────────┐                         │
│ Grantee  │ ─── Execute Msg ───────►│
│ (Bot)    │    (on behalf of        │
└──────────┘     granter)            │
```

1. Granter creates authorization on-chain
2. Grantee constructs messages with granter's address as owner
3. Grantee wraps messages in `MsgExec`
4. Chain verifies authorization exists
5. Message executes as if sent by granter

## Related Documentation

- **@granting-permissions.md** - Detailed granting guide
- **@using-grants.md** - Using grants programmatically
