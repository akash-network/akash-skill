# Granting Permissions

How to create and manage AuthZ grants on Akash.

## Creating Grants

### Generic Authorization

Grant permission for specific message types:

```bash
provider-services tx authz grant <GRANTEE_ADDRESS> generic \
  --msg-type <MSG_TYPE_URL> \
  --from <GRANTER_KEY> \
  --expiration "2025-12-31T23:59:59Z"
```

### Common Deployment Grants

```bash
GRANTEE="akash1grantee..."

# Full deployment lifecycle
provider-services tx authz grant $GRANTEE generic \
  --msg-type /akash.deployment.v1beta4.MsgCreateDeployment \
  --from granter

provider-services tx authz grant $GRANTEE generic \
  --msg-type /akash.deployment.v1beta4.MsgUpdateDeployment \
  --from granter

provider-services tx authz grant $GRANTEE generic \
  --msg-type /akash.deployment.v1beta4.MsgCloseDeployment \
  --from granter

provider-services tx authz grant $GRANTEE generic \
  --msg-type /akash.deployment.v1beta4.MsgDepositDeployment \
  --from granter

# Lease management
provider-services tx authz grant $GRANTEE generic \
  --msg-type /akash.market.v1beta5.MsgCreateLease \
  --from granter
```

### Fee Grant

Allow grantee to use granter's funds for fees:

```bash
# Unlimited fee grant
provider-services tx feegrant grant $(provider-services keys show granter -a) $GRANTEE \
  --from granter

# With limit
provider-services tx feegrant grant $(provider-services keys show granter -a) $GRANTEE \
  --spend-limit 10000000uakt \
  --from granter

# With time expiration
provider-services tx feegrant grant $(provider-services keys show granter -a) $GRANTEE \
  --expiration "2025-06-30T00:00:00Z" \
  --from granter

# With both
provider-services tx feegrant grant $(provider-services keys show granter -a) $GRANTEE \
  --spend-limit 10000000uakt \
  --expiration "2025-06-30T00:00:00Z" \
  --from granter
```

## Grant Expiration

### Set Expiration on Grant

```bash
provider-services tx authz grant $GRANTEE generic \
  --msg-type /akash.deployment.v1beta4.MsgCreateDeployment \
  --expiration "2025-12-31T23:59:59Z" \
  --from granter
```

### No Expiration

Omit `--expiration` for indefinite grants (not recommended for production).

## Query Grants

### List All Grants from Address

```bash
provider-services query authz grants-by-granter $(provider-services keys show granter -a)
```

### List All Grants to Address

```bash
provider-services query authz grants-by-grantee $(provider-services keys show grantee -a)
```

### Query Specific Grant

```bash
provider-services query authz grants \
  $(provider-services keys show granter -a) \
  $(provider-services keys show grantee -a) \
  /akash.deployment.v1beta4.MsgCreateDeployment
```

### Query Fee Grants

```bash
provider-services query feegrant grants-by-granter $(provider-services keys show granter -a)
provider-services query feegrant grants-by-grantee $(provider-services keys show grantee -a)
```

## Revoke Grants

### Revoke AuthZ Grant

```bash
provider-services tx authz revoke $GRANTEE \
  /akash.deployment.v1beta4.MsgCreateDeployment \
  --from granter
```

### Revoke Fee Grant

```bash
provider-services tx feegrant revoke $(provider-services keys show granter -a) $GRANTEE \
  --from granter
```

### Revoke All

Revoke each grant individually - there's no batch revoke.

## Security Best Practices

1. **Always set expiration** - Prevents indefinite access
2. **Grant minimum permissions** - Only what's needed
3. **Use separate grantee accounts** - Don't reuse keys
4. **Monitor grants** - Regularly audit active grants
5. **Revoke when done** - Clean up unused grants
6. **Use fee limits** - Set spending limits on fee grants

## Message Type Reference

| Message Type | Purpose |
|-------------|---------|
| `/akash.deployment.v1beta4.MsgCreateDeployment` | Create deployment |
| `/akash.deployment.v1beta4.MsgUpdateDeployment` | Update deployment |
| `/akash.deployment.v1beta4.MsgCloseDeployment` | Close deployment |
| `/akash.deployment.v1beta4.MsgDepositDeployment` | Deposit to deployment |
| `/akash.market.v1beta5.MsgCreateLease` | Create lease |
| `/akash.cert.v1.MsgCreateCertificate` | Create certificate |
| `/akash.cert.v1.MsgRevokeCertificate` | Revoke certificate |
