# TypeScript Chain SDK (Browser)

Using the Akash TypeScript SDK for blockchain interactions in web browsers.

## Browser Setup

### With Bundler (Vite, Webpack)

```typescript
import { SigningStargateClient } from "@cosmjs/stargate";
import { getAkashTypeRegistry } from "@akashnetwork/akashjs/build/stargate";
```

### Polyfills

Some environments need Node.js polyfills:

```typescript
// vite.config.ts
import { defineConfig } from "vite";
import { nodePolyfills } from "vite-plugin-node-polyfills";

export default defineConfig({
  plugins: [nodePolyfills()]
});
```

## Wallet Integration

### Keplr Wallet

```typescript
import { SigningStargateClient } from "@cosmjs/stargate";
import { getAkashTypeRegistry } from "@akashnetwork/akashjs/build/stargate";

const CHAIN_ID = "akashnet-2";
const RPC_ENDPOINT = "https://rpc.akashnet.net:443";

async function connectKeplr() {
  // Check if Keplr is installed
  if (!window.keplr) {
    throw new Error("Keplr wallet not found");
  }

  // Enable Akash chain
  await window.keplr.enable(CHAIN_ID);

  // Get offline signer
  const offlineSigner = window.keplr.getOfflineSigner(CHAIN_ID);

  // Get account
  const accounts = await offlineSigner.getAccounts();
  const address = accounts[0].address;

  // Create signing client
  const registry = getAkashTypeRegistry();
  const client = await SigningStargateClient.connectWithSigner(
    RPC_ENDPOINT,
    offlineSigner,
    { registry }
  );

  return { client, address };
}
```

### Leap Wallet

```typescript
async function connectLeap() {
  if (!window.leap) {
    throw new Error("Leap wallet not found");
  }

  await window.leap.enable(CHAIN_ID);
  const offlineSigner = window.leap.getOfflineSigner(CHAIN_ID);
  const accounts = await offlineSigner.getAccounts();

  const registry = getAkashTypeRegistry();
  const client = await SigningStargateClient.connectWithSigner(
    RPC_ENDPOINT,
    offlineSigner,
    { registry }
  );

  return { client, address: accounts[0].address };
}
```

### Multi-Wallet Support

```typescript
type WalletType = "keplr" | "leap" | "cosmostation";

async function connectWallet(walletType: WalletType) {
  const wallets: Record<WalletType, any> = {
    keplr: window.keplr,
    leap: window.leap,
    cosmostation: window.cosmostation?.providers?.keplr
  };

  const wallet = wallets[walletType];
  if (!wallet) {
    throw new Error(`${walletType} wallet not found`);
  }

  await wallet.enable(CHAIN_ID);
  const offlineSigner = wallet.getOfflineSigner(CHAIN_ID);
  const accounts = await offlineSigner.getAccounts();

  const registry = getAkashTypeRegistry();
  const client = await SigningStargateClient.connectWithSigner(
    RPC_ENDPOINT,
    offlineSigner,
    { registry }
  );

  return { client, address: accounts[0].address, wallet: walletType };
}
```

## React Integration

### Wallet Context

```typescript
import React, { createContext, useContext, useState, useCallback } from "react";
import { SigningStargateClient } from "@cosmjs/stargate";
import { getAkashTypeRegistry } from "@akashnetwork/akashjs/build/stargate";

interface WalletContextType {
  client: SigningStargateClient | null;
  address: string | null;
  connect: () => Promise<void>;
  disconnect: () => void;
  isConnected: boolean;
}

const WalletContext = createContext<WalletContextType | null>(null);

export function WalletProvider({ children }: { children: React.ReactNode }) {
  const [client, setClient] = useState<SigningStargateClient | null>(null);
  const [address, setAddress] = useState<string | null>(null);

  const connect = useCallback(async () => {
    if (!window.keplr) {
      alert("Please install Keplr wallet");
      return;
    }

    await window.keplr.enable("akashnet-2");
    const offlineSigner = window.keplr.getOfflineSigner("akashnet-2");
    const accounts = await offlineSigner.getAccounts();

    const registry = getAkashTypeRegistry();
    const stargateClient = await SigningStargateClient.connectWithSigner(
      "https://rpc.akashnet.net:443",
      offlineSigner,
      { registry }
    );

    setClient(stargateClient);
    setAddress(accounts[0].address);
  }, []);

  const disconnect = useCallback(() => {
    if (client) {
      client.disconnect();
    }
    setClient(null);
    setAddress(null);
  }, [client]);

  return (
    <WalletContext.Provider
      value={{
        client,
        address,
        connect,
        disconnect,
        isConnected: !!client
      }}
    >
      {children}
    </WalletContext.Provider>
  );
}

export function useWallet() {
  const context = useContext(WalletContext);
  if (!context) {
    throw new Error("useWallet must be used within WalletProvider");
  }
  return context;
}
```

### Usage in Components

```typescript
function DeployButton() {
  const { client, address, isConnected, connect } = useWallet();
  const [deploying, setDeploying] = useState(false);

  const handleDeploy = async () => {
    if (!client || !address) return;

    setDeploying(true);
    try {
      // Create deployment message
      const msg = {
        typeUrl: "/akash.deployment.v1beta3.MsgCreateDeployment",
        value: {
          id: { owner: address, dseq: BigInt(Date.now()) },
          groups: [],  // Add your groups
          version: new Uint8Array(),
          deposit: { denom: "uact", amount: "5000000" },
          depositor: address
        }
      };

      const result = await client.signAndBroadcast(address, [msg], "auto");
      console.log("Deployment created:", result.transactionHash);
    } catch (error) {
      console.error("Deployment failed:", error);
    } finally {
      setDeploying(false);
    }
  };

  if (!isConnected) {
    return <button onClick={connect}>Connect Wallet</button>;
  }

  return (
    <button onClick={handleDeploy} disabled={deploying}>
      {deploying ? "Deploying..." : "Deploy"}
    </button>
  );
}
```

### Custom Hooks

```typescript
import { useCallback, useState } from "react";
import { useWallet } from "./WalletContext";

export function useDeployment() {
  const { client, address } = useWallet();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const createDeployment = useCallback(
    async (sdl: string, deposit: string = "5000000") => {
      if (!client || !address) {
        throw new Error("Wallet not connected");
      }

      setLoading(true);
      setError(null);

      try {
        const dseq = Date.now().toString();

        const msg = {
          typeUrl: "/akash.deployment.v1beta3.MsgCreateDeployment",
          value: {
            id: { owner: address, dseq: BigInt(dseq) },
            groups: [],  // Parse from SDL
            version: new Uint8Array(),
            deposit: { denom: "uact", amount: deposit },
            depositor: address
          }
        };

        const result = await client.signAndBroadcast(address, [msg], "auto");
        return { dseq, txHash: result.transactionHash };
      } catch (err) {
        setError(err as Error);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [client, address]
  );

  return { createDeployment, loading, error };
}
```

## TypeScript Types

### Window Interface

```typescript
// types/global.d.ts
interface Window {
  keplr?: {
    enable: (chainId: string) => Promise<void>;
    getOfflineSigner: (chainId: string) => OfflineSigner;
    signArbitrary: (
      chainId: string,
      signer: string,
      data: string
    ) => Promise<{ signature: string; pub_key: { type: string; value: string } }>;
  };
  leap?: {
    enable: (chainId: string) => Promise<void>;
    getOfflineSigner: (chainId: string) => OfflineSigner;
  };
  cosmostation?: {
    providers: {
      keplr: {
        enable: (chainId: string) => Promise<void>;
        getOfflineSigner: (chainId: string) => OfflineSigner;
      };
    };
  };
}
```

## Security Considerations

### Transaction Confirmation

Always show transaction details before signing:

```typescript
async function confirmAndSign(
  client: SigningStargateClient,
  address: string,
  messages: any[]
) {
  // Show confirmation dialog
  const confirmed = await showConfirmationDialog({
    title: "Confirm Transaction",
    messages: messages.map(m => ({
      type: m.typeUrl,
      details: JSON.stringify(m.value, null, 2)
    }))
  });

  if (!confirmed) {
    throw new Error("Transaction cancelled");
  }

  return client.signAndBroadcast(address, messages, "auto");
}
```

### Gas Estimation Display

```typescript
async function estimateAndConfirmGas(
  client: SigningStargateClient,
  address: string,
  messages: any[]
) {
  // Estimate gas
  const gasEstimation = await client.simulate(address, messages, undefined);
  const gasLimit = Math.ceil(gasEstimation * 1.3); // 30% buffer
  const gasPrice = 0.025; // uakt per gas
  const estimatedFee = (gasLimit * gasPrice).toFixed(0);

  const confirmed = await showConfirmationDialog({
    title: "Confirm Transaction Fee",
    message: `Estimated fee: ${estimatedFee} uakt (~${gasLimit} gas)`
  });

  if (!confirmed) throw new Error("Cancelled");

  return client.signAndBroadcast(address, messages, {
    amount: [{ denom: "uakt", amount: estimatedFee }],
    gas: gasLimit.toString()
  });
}
```

## Error Handling

```typescript
function handleWalletError(error: unknown): string {
  if (error instanceof Error) {
    // User rejected
    if (error.message.includes("rejected")) {
      return "Transaction was rejected";
    }

    // Insufficient funds
    if (error.message.includes("insufficient")) {
      return "Insufficient balance";
    }

    // Network error
    if (error.message.includes("network") || error.message.includes("fetch")) {
      return "Network error - please check your connection";
    }

    return error.message;
  }

  return "An unknown error occurred";
}

// Usage
try {
  await client.signAndBroadcast(address, messages, "auto");
} catch (error) {
  const message = handleWalletError(error);
  showErrorToast(message);
}
```

## Testing

### Mock Wallet for Tests

```typescript
const mockWallet = {
  getAccounts: async () => [
    { address: "akash1test...", pubkey: new Uint8Array() }
  ],
  signDirect: async () => ({
    signed: {},
    signature: { signature: "", pub_key: { type: "", value: "" } }
  })
};

// In tests
jest.mock("@cosmjs/stargate", () => ({
  SigningStargateClient: {
    connectWithSigner: jest.fn().mockResolvedValue({
      signAndBroadcast: jest.fn().mockResolvedValue({
        code: 0,
        transactionHash: "test-hash"
      })
    })
  }
}));
```
