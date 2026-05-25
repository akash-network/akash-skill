# Granting Permissions

How to create and manage AuthZ grants on Akash.

## Creating Grants

### Generic Authorization

Grant permission for specific message types:

```bash
akash tx authz grant <GRANTEE_ADDRESS> generic \
  --msg-type <MSG_TYPE_URL> \
  --from <GRANTER_KEY> \
  --expiration "2025-12-31T23:59:59Z"
```

### Common Deployment Grants

```bash
GRANTEE="akash1grantee..."

# Full deployment lifecycle
akash tx authz grant $GRANTEE generic \
  --msg-type /akash.deployment.v1beta3.MsgCreateDeployment \
  --from granter

akash tx authz grant $GRANTEE generic \
  --msg-type /akash.deployment.v1beta3.MsgUpdateDeployment \
  --from granter

akash tx authz grant $GRANTEE generic \
  --msg-type /akash.deployment.v1beta3.MsgCloseDeployment \
  --from granter

akash tx authz grant $GRANTEE generic \
  --msg-type /akash.deployment.v1beta3.MsgDepositDeployment \
  --from granter

# Lease management
akash tx authz grant $GRANTEE generic \
  --msg-type /akash.market.v1beta4.MsgCreateLease \
  --from granter
```

### Fee Grant

Allow grantee to use granter's funds for fees:

```bash
# Unlimited fee grant
akash tx feegrant grant $(akash keys show granter -a) $GRANTEE \
  --from granter

# With limit
akash tx feegrant grant $(akash keys show granter -a) $GRANTEE \
  --spend-limit 10000000uakt \
  --from granter

# With time expiration
akash tx feegrant grant $(akash keys show granter -a) $GRANTEE \
  --expiration "2025-06-30T00:00:00Z" \
  --from granter

# With both
akash tx feegrant grant $(akash keys show granter -a) $GRANTEE \
  --spend-limit 10000000uakt \
  --expiration "2025-06-30T00:00:00Z" \
  --from granter
```

## Grant Expiration

### Set Expiration on Grant

```bash
akash tx authz grant $GRANTEE generic \
  --msg-type /akash.deployment.v1beta3.MsgCreateDeployment \
  --expiration "2025-12-31T23:59:59Z" \
  --from granter
```

### No Expiration

Omit `--expiration` for indefinite grants (not recommended for production).

## Query Grants

### List All Grants from Address

```bash
akash query authz grants-by-granter $(akash keys show granter -a)
```

### List All Grants to Address

```bash
akash query authz grants-by-grantee $(akash keys show grantee -a)
```

### Query Specific Grant

```bash
akash query authz grants \
  $(akash keys show granter -a) \
  $(akash keys show grantee -a) \
  /akash.deployment.v1beta3.MsgCreateDeployment
```

### Query Fee Grants

```bash
akash query feegrant grants-by-granter $(akash keys show granter -a)
akash query feegrant grants-by-grantee $(akash keys show grantee -a)
```

## Revoke Grants

### Revoke AuthZ Grant

```bash
akash tx authz revoke $GRANTEE \
  /akash.deployment.v1beta3.MsgCreateDeployment \
  --from granter
```

### Revoke Fee Grant

```bash
akash tx feegrant revoke $(akash keys show granter -a) $GRANTEE \
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
| `/akash.deployment.v1beta3.MsgCreateDeployment` | Create deployment |
| `/akash.deployment.v1beta3.MsgUpdateDeployment` | Update deployment |
| `/akash.deployment.v1beta3.MsgCloseDeployment` | Close deployment |
| `/akash.deployment.v1beta3.MsgDepositDeployment` | Deposit to deployment |
| `/akash.market.v1beta4.MsgCreateLease` | Create lease |
| `/akash.cert.v1beta3.MsgCreateCertificate` | Create certificate |
| `/akash.cert.v1beta3.MsgRevokeCertificate` | Revoke certificate |
