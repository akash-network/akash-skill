# TypeScript Chain SDK (Node.js)

Using the Akash TypeScript SDK for blockchain interactions in Node.js.

## Setup

```typescript
import { DirectSecp256k1HdWallet } from "@cosmjs/proto-signing";
import { SigningStargateClient, GasPrice } from "@cosmjs/stargate";
import { getAkashTypeRegistry } from "@akashnetwork/akashjs/build/stargate";

const RPC_ENDPOINT = "https://rpc.akashnet.net:443";

async function createClient(mnemonic: string) {
  const wallet = await DirectSecp256k1HdWallet.fromMnemonic(mnemonic, {
    prefix: "akash"
  });

  const [account] = await wallet.getAccounts();
  const registry = getAkashTypeRegistry();

  const client = await SigningStargateClient.connectWithSigner(
    RPC_ENDPOINT,
    wallet,
    {
      registry,
      gasPrice: GasPrice.fromString("0.025uakt")
    }
  );

  return { client, address: account.address };
}
```

## Query Operations

### Query Account Balance

```typescript
async function getBalance(client: SigningStargateClient, address: string) {
  const balance = await client.getBalance(address, "uact");
  console.log(`Balance: ${balance.amount} uact`);
  return balance;
}
```

### Query Deployment

```typescript
import { QueryClientImpl as DeploymentQueryClient } from "@akashnetwork/akash-api/akash/deployment/v1beta3";

async function getDeployment(client: SigningStargateClient, owner: string, dseq: string) {
  const queryClient = new DeploymentQueryClient(client.getQueryClient()!);

  const response = await queryClient.Deployment({
    id: {
      owner,
      dseq: BigInt(dseq)
    }
  });

  return response.deployment;
}
```

### Query Leases

```typescript
import { QueryClientImpl as MarketQueryClient } from "@akashnetwork/akash-api/akash/market/v1beta4";

async function getLeases(client: SigningStargateClient, owner: string) {
  const queryClient = new MarketQueryClient(client.getQueryClient()!);

  const response = await queryClient.Leases({
    filters: {
      owner,
      state: "active"
    }
  });

  return response.leases;
}
```

## Transaction Operations

### Create Deployment

```typescript
import { MsgCreateDeployment } from "@akashnetwork/akash-api/akash/deployment/v1beta3";
import { SDL } from "@akashnetwork/akashjs/build/sdl";

async function createDeployment(
  client: SigningStargateClient,
  address: string,
  sdlContent: string,
  deposit: string = "5000000"
) {
  // Parse SDL
  const sdl = SDL.fromString(sdlContent);
  const manifest = sdl.manifest();
  const groups = sdl.groups();

  // Get next deployment sequence
  const dseq = Date.now(); // Use timestamp as dseq

  const msg: MsgCreateDeployment = {
    id: {
      owner: address,
      dseq: BigInt(dseq)
    },
    groups,
    version: await sdl.manifestVersion(),
    deposit: {
      denom: "uact",
      amount: deposit
    },
    depositor: address
  };

  const result = await client.signAndBroadcast(
    address,
    [{ typeUrl: "/akash.deployment.v1beta3.MsgCreateDeployment", value: msg }],
    "auto"
  );

  if (result.code !== 0) {
    throw new Error(`Transaction failed: ${result.rawLog}`);
  }

  return { dseq: dseq.toString(), txHash: result.transactionHash };
}
```

### Accept Bid (Create Lease)

```typescript
import { MsgCreateLease } from "@akashnetwork/akash-api/akash/market/v1beta4";

async function createLease(
  client: SigningStargateClient,
  address: string,
  dseq: string,
  gseq: number,
  oseq: number,
  provider: string
) {
  const msg: MsgCreateLease = {
    bidId: {
      owner: address,
      dseq: BigInt(dseq),
      gseq,
      oseq,
      provider
    }
  };

  const result = await client.signAndBroadcast(
    address,
    [{ typeUrl: "/akash.market.v1beta4.MsgCreateLease", value: msg }],
    "auto"
  );

  if (result.code !== 0) {
    throw new Error(`Transaction failed: ${result.rawLog}`);
  }

  return result.transactionHash;
}
```

### Close Deployment

```typescript
import { MsgCloseDeployment } from "@akashnetwork/akash-api/akash/deployment/v1beta3";

async function closeDeployment(
  client: SigningStargateClient,
  address: string,
  dseq: string
) {
  const msg: MsgCloseDeployment = {
    id: {
      owner: address,
      dseq: BigInt(dseq)
    }
  };

  const result = await client.signAndBroadcast(
    address,
    [{ typeUrl: "/akash.deployment.v1beta3.MsgCloseDeployment", value: msg }],
    "auto"
  );

  return result.transactionHash;
}
```

### Deposit to Deployment

```typescript
import { MsgDepositDeployment } from "@akashnetwork/akash-api/akash/deployment/v1beta3";

async function depositToDeployment(
  client: SigningStargateClient,
  address: string,
  dseq: string,
  amount: string
) {
  const msg: MsgDepositDeployment = {
    id: {
      owner: address,
      dseq: BigInt(dseq)
    },
    amount: {
      denom: "uact",
      amount
    },
    depositor: address
  };

  const result = await client.signAndBroadcast(
    address,
    [{ typeUrl: "/akash.deployment.v1beta3.MsgDepositDeployment", value: msg }],
    "auto"
  );

  return result.transactionHash;
}
```

## Complete Deployment Flow

```typescript
import { DirectSecp256k1HdWallet } from "@cosmjs/proto-signing";
import { SigningStargateClient, GasPrice } from "@cosmjs/stargate";
import { getAkashTypeRegistry } from "@akashnetwork/akashjs/build/stargate";
import { SDL } from "@akashnetwork/akashjs/build/sdl";
import { sendManifest } from "@akashnetwork/akashjs/build/provider";
import { certificateManager } from "@akashnetwork/akashjs/build/certificates";

async function deployToAkash(mnemonic: string, sdlContent: string) {
  // 1. Setup client
  const wallet = await DirectSecp256k1HdWallet.fromMnemonic(mnemonic, {
    prefix: "akash"
  });
  const [account] = await wallet.getAccounts();
  const registry = getAkashTypeRegistry();

  const client = await SigningStargateClient.connectWithSigner(
    "https://rpc.akashnet.net:443",
    wallet,
    { registry, gasPrice: GasPrice.fromString("0.025uakt") }
  );

  const address = account.address;
  console.log(`Deploying from: ${address}`);

  // 2. Create/get certificate
  const cert = await certificateManager.createCertificate(address);

  // 3. Parse SDL
  const sdl = SDL.fromString(sdlContent);
  const groups = sdl.groups();

  // 4. Create deployment
  const dseq = Date.now().toString();
  const createDeploymentMsg = {
    typeUrl: "/akash.deployment.v1beta3.MsgCreateDeployment",
    value: {
      id: { owner: address, dseq: BigInt(dseq) },
      groups,
      version: await sdl.manifestVersion(),
      deposit: { denom: "uact", amount: "5000000" },
      depositor: address
    }
  };

  const deployResult = await client.signAndBroadcast(address, [createDeploymentMsg], "auto");
  console.log(`Deployment created: ${dseq}`);

  // 5. Wait for bids (simplified - in production, poll for bids)
  console.log("Waiting for bids...");
  await new Promise(r => setTimeout(r, 30000));

  // 6. Query bids and select provider
  // (Implementation depends on your bid selection logic)
  const selectedProvider = "akash1..."; // Select from available bids

  // 7. Create lease
  const createLeaseMsg = {
    typeUrl: "/akash.market.v1beta4.MsgCreateLease",
    value: {
      bidId: {
        owner: address,
        dseq: BigInt(dseq),
        gseq: 1,
        oseq: 1,
        provider: selectedProvider
      }
    }
  };

  const leaseResult = await client.signAndBroadcast(address, [createLeaseMsg], "auto");
  console.log(`Lease created with provider: ${selectedProvider}`);

  // 8. Send manifest to provider
  const manifest = sdl.manifest();
  await sendManifest(
    {
      dseq,
      gseq: 1,
      oseq: 1,
      owner: address,
      provider: selectedProvider
    },
    manifest,
    cert
  );

  console.log("Deployment complete!");
  return { dseq, provider: selectedProvider };
}
```

## Error Handling

```typescript
import { isDeliverTxFailure } from "@cosmjs/stargate";

async function safeTransaction(
  client: SigningStargateClient,
  address: string,
  messages: any[]
) {
  try {
    const result = await client.signAndBroadcast(address, messages, "auto");

    if (isDeliverTxFailure(result)) {
      throw new Error(`Transaction failed: ${result.rawLog}`);
    }

    return result;
  } catch (error) {
    if (error instanceof Error) {
      if (error.message.includes("insufficient funds")) {
        throw new Error("Insufficient balance for transaction");
      }
      if (error.message.includes("account sequence mismatch")) {
        throw new Error("Transaction sequence error - retry");
      }
    }
    throw error;
  }
}
```

## Best Practices

### Gas Estimation

```typescript
// Let the SDK estimate gas
const result = await client.signAndBroadcast(address, messages, "auto");

// Or set explicit gas
const result = await client.signAndBroadcast(address, messages, {
  amount: [{ denom: "uakt", amount: "5000" }],
  gas: "200000"
});
```

### Connection Management

```typescript
class AkashClient {
  private client: SigningStargateClient | null = null;

  async connect(mnemonic: string) {
    if (this.client) return this.client;

    const wallet = await DirectSecp256k1HdWallet.fromMnemonic(mnemonic, {
      prefix: "akash"
    });

    this.client = await SigningStargateClient.connectWithSigner(
      "https://rpc.akashnet.net:443",
      wallet,
      { registry: getAkashTypeRegistry() }
    );

    return this.client;
  }

  async disconnect() {
    if (this.client) {
      this.client.disconnect();
      this.client = null;
    }
  }
}
```

### Retry Logic

```typescript
async function withRetry<T>(
  fn: () => Promise<T>,
  maxRetries = 3,
  delay = 1000
): Promise<T> {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      await new Promise(r => setTimeout(r, delay * Math.pow(2, i)));
    }
  }
  throw new Error("Max retries exceeded");
}

// Usage
const result = await withRetry(() =>
  client.signAndBroadcast(address, messages, "auto")
);
```
