# Using AuthZ Grants

Execute transactions on behalf of a granter using AuthZ.

## CLI Usage

### Execute as Grantee

Wrap any authorized message in `MsgExec`:

```bash
# Create deployment on behalf of granter
akash tx authz exec <(akash tx deployment create deploy.yaml \
  --from <GRANTER_ADDRESS> \
  --generate-only) \
  --from grantee
```

### Step-by-Step Example

```bash
GRANTER="akash1granter..."
GRANTEE_KEY="grantee"

# 1. Generate unsigned deployment tx (from granter's perspective)
akash tx deployment create deploy.yaml \
  --from $GRANTER \
  --generate-only > unsigned_tx.json

# 2. Execute as grantee
akash tx authz exec unsigned_tx.json \
  --from $GRANTEE_KEY

# Clean up
rm unsigned_tx.json
```

### With Fee Grant

```bash
# Execute and use granter's fees
akash tx authz exec unsigned_tx.json \
  --from $GRANTEE_KEY \
  --fee-granter $GRANTER
```

## TypeScript Usage

### Execute Grant with SDK

```typescript
import { MsgExec } from "cosmjs-types/cosmos/authz/v1beta1/tx";
import { MsgCreateDeployment } from "@akashnetwork/akash-api/akash/deployment/v1beta3";

async function executeAsGrantee(
  client: SigningStargateClient,
  granteeAddress: string,
  granterAddress: string,
  sdl: SDL
) {
  // Build the inner message (from granter's perspective)
  const innerMsg = MsgCreateDeployment.fromPartial({
    id: {
      owner: granterAddress,  // Granter is the deployment owner
      dseq: BigInt(Date.now())
    },
    groups: sdl.groups(),
    version: await sdl.manifestVersion(),
    deposit: { denom: "uact", amount: "5000000" },
    depositor: granterAddress
  });

  // Wrap in MsgExec
  const execMsg = {
    typeUrl: "/cosmos.authz.v1beta1.MsgExec",
    value: MsgExec.fromPartial({
      grantee: granteeAddress,
      msgs: [
        {
          typeUrl: "/akash.deployment.v1beta3.MsgCreateDeployment",
          value: MsgCreateDeployment.encode(innerMsg).finish()
        }
      ]
    })
  };

  // Sign and broadcast as grantee
  const result = await client.signAndBroadcast(
    granteeAddress,
    [execMsg],
    "auto"
  );

  return result;
}
```

### Grant Creation with SDK

```typescript
import { MsgGrant } from "cosmjs-types/cosmos/authz/v1beta1/tx";
import { GenericAuthorization } from "cosmjs-types/cosmos/authz/v1beta1/authz";

async function createGrant(
  client: SigningStargateClient,
  granterAddress: string,
  granteeAddress: string,
  msgTypeUrl: string,
  expirationDate: Date
) {
  const authorization = GenericAuthorization.fromPartial({
    msg: msgTypeUrl
  });

  const msg = {
    typeUrl: "/cosmos.authz.v1beta1.MsgGrant",
    value: MsgGrant.fromPartial({
      granter: granterAddress,
      grantee: granteeAddress,
      grant: {
        authorization: {
          typeUrl: "/cosmos.authz.v1beta1.GenericAuthorization",
          value: GenericAuthorization.encode(authorization).finish()
        },
        expiration: {
          seconds: BigInt(Math.floor(expirationDate.getTime() / 1000)),
          nanos: 0
        }
      }
    })
  };

  return client.signAndBroadcast(granterAddress, [msg], "auto");
}
```

### Complete Automation Example

```typescript
class AkashAutomation {
  private granteeClient: SigningStargateClient;
  private granteeAddress: string;
  private granterAddress: string;

  constructor(
    granteeClient: SigningStargateClient,
    granteeAddress: string,
    granterAddress: string
  ) {
    this.granteeClient = granteeClient;
    this.granteeAddress = granteeAddress;
    this.granterAddress = granterAddress;
  }

  async createDeployment(sdlContent: string) {
    const sdl = SDL.fromString(sdlContent);
    const dseq = Date.now().toString();

    const innerMsg = MsgCreateDeployment.fromPartial({
      id: { owner: this.granterAddress, dseq: BigInt(dseq) },
      groups: sdl.groups(),
      version: await sdl.manifestVersion(),
      deposit: { denom: "uact", amount: "5000000" },
      depositor: this.granterAddress
    });

    const execMsg = {
      typeUrl: "/cosmos.authz.v1beta1.MsgExec",
      value: MsgExec.fromPartial({
        grantee: this.granteeAddress,
        msgs: [{
          typeUrl: "/akash.deployment.v1beta3.MsgCreateDeployment",
          value: MsgCreateDeployment.encode(innerMsg).finish()
        }]
      })
    };

    const result = await this.granteeClient.signAndBroadcast(
      this.granteeAddress,
      [execMsg],
      "auto"
    );

    return { dseq, txHash: result.transactionHash };
  }

  async closeDeployment(dseq: string) {
    const innerMsg = MsgCloseDeployment.fromPartial({
      id: { owner: this.granterAddress, dseq: BigInt(dseq) }
    });

    const execMsg = {
      typeUrl: "/cosmos.authz.v1beta1.MsgExec",
      value: MsgExec.fromPartial({
        grantee: this.granteeAddress,
        msgs: [{
          typeUrl: "/akash.deployment.v1beta3.MsgCloseDeployment",
          value: MsgCloseDeployment.encode(innerMsg).finish()
        }]
      })
    };

    return this.granteeClient.signAndBroadcast(
      this.granteeAddress,
      [execMsg],
      "auto"
    );
  }
}
```

## Error Handling

### Authorization Not Found

```
authorization not found: unauthorized
```

**Cause:** Grant doesn't exist or has expired.

**Solution:** Create or renew the grant.

### Unauthorized Message Type

```
unauthorized: authorization not found
```

**Cause:** The grant doesn't cover the message type being executed.

**Solution:** Grant the specific message type needed.

### Expired Grant

```
authorization expired
```

**Cause:** Grant expiration date has passed.

**Solution:** Create a new grant with updated expiration.

## Monitoring Grants

### Check Grant Status

```bash
# Verify grant exists
akash query authz grants \
  $(akash keys show granter -a) \
  $(akash keys show grantee -a)
```

### Automated Monitoring

```typescript
async function checkGrantValid(
  client: StargateClient,
  granterAddress: string,
  granteeAddress: string,
  msgType: string
): Promise<boolean> {
  try {
    const grants = await client.queryClient.authz.grants(
      granterAddress,
      granteeAddress,
      msgType
    );
    return grants.grants.length > 0;
  } catch {
    return false;
  }
}
```
