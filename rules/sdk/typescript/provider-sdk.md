# Provider SDK

Communicating with Akash providers using the TypeScript SDK.

## Overview

After creating a lease, you need to:
1. Generate/retrieve a client certificate
2. Send the manifest to the provider
3. Query lease status and logs
4. Manage the deployment

## Certificate Management

### Create Certificate

```typescript
import { certificateManager } from "@akashnetwork/akashjs/build/certificates";

async function createCertificate(address: string) {
  // Generate new certificate
  const cert = await certificateManager.createCertificate(address);

  // Store certificate securely
  localStorage.setItem(`akash-cert-${address}`, JSON.stringify({
    cert: cert.cert,
    privateKey: cert.privateKey,
    publicKey: cert.publicKey
  }));

  return cert;
}
```

### Broadcast Certificate On-Chain

```typescript
import { MsgCreateCertificate } from "@akashnetwork/akash-api/akash/cert/v1beta3";

async function broadcastCertificate(
  client: SigningStargateClient,
  address: string,
  cert: { cert: string; publicKey: string }
) {
  const msg: MsgCreateCertificate = {
    owner: address,
    cert: Buffer.from(cert.cert).toString("base64"),
    pubkey: Buffer.from(cert.publicKey).toString("base64")
  };

  const result = await client.signAndBroadcast(
    address,
    [{ typeUrl: "/akash.cert.v1beta3.MsgCreateCertificate", value: msg }],
    "auto"
  );

  return result;
}
```

### Load Existing Certificate

```typescript
function loadCertificate(address: string) {
  const stored = localStorage.getItem(`akash-cert-${address}`);
  if (!stored) {
    throw new Error("No certificate found - create one first");
  }
  return JSON.parse(stored);
}
```

## Sending Manifest

### Basic Manifest Send

```typescript
import { sendManifest } from "@akashnetwork/akashjs/build/provider";
import { SDL } from "@akashnetwork/akashjs/build/sdl";

async function sendManifestToProvider(
  leaseId: {
    owner: string;
    dseq: string;
    gseq: number;
    oseq: number;
    provider: string;
  },
  sdlContent: string,
  certificate: { cert: string; privateKey: string }
) {
  // Parse SDL to get manifest
  const sdl = SDL.fromString(sdlContent);
  const manifest = sdl.manifest();

  // Send to provider
  await sendManifest(leaseId, manifest, certificate);

  console.log("Manifest sent successfully");
}
```

### With Error Handling

```typescript
async function sendManifestWithRetry(
  leaseId: any,
  sdlContent: string,
  certificate: any,
  maxRetries = 3
) {
  const sdl = SDL.fromString(sdlContent);
  const manifest = sdl.manifest();

  for (let i = 0; i < maxRetries; i++) {
    try {
      await sendManifest(leaseId, manifest, certificate);
      return true;
    } catch (error) {
      console.warn(`Manifest send attempt ${i + 1} failed:`, error);

      if (i === maxRetries - 1) {
        throw new Error(`Failed to send manifest after ${maxRetries} attempts`);
      }

      // Wait before retry (exponential backoff)
      await new Promise(r => setTimeout(r, 1000 * Math.pow(2, i)));
    }
  }
}
```

## Querying Provider

### Get Lease Status

```typescript
import { queryLeaseStatus } from "@akashnetwork/akashjs/build/provider";

async function getLeaseStatus(
  leaseId: {
    owner: string;
    dseq: string;
    gseq: number;
    oseq: number;
    provider: string;
  },
  certificate: { cert: string; privateKey: string }
) {
  const status = await queryLeaseStatus(leaseId, certificate);

  return {
    services: status.services,
    forwardedPorts: status.forwarded_ports
  };
}
```

### Get Service URIs

```typescript
async function getServiceUris(leaseId: any, certificate: any) {
  const status = await queryLeaseStatus(leaseId, certificate);

  const uris: Record<string, string[]> = {};

  for (const [serviceName, service] of Object.entries(status.services)) {
    uris[serviceName] = (service as any).uris || [];
  }

  return uris;
}
```

### Stream Logs

```typescript
import { queryLeaseLogs } from "@akashnetwork/akashjs/build/provider";

async function streamLogs(
  leaseId: any,
  certificate: any,
  options: {
    service?: string;
    follow?: boolean;
    tail?: number;
  } = {}
) {
  const logs = await queryLeaseLogs(leaseId, certificate, {
    services: options.service ? [options.service] : undefined,
    follow: options.follow || false,
    tail: options.tail || 100
  });

  return logs;
}
```

### Interactive Shell

```typescript
import { leaseShell } from "@akashnetwork/akashjs/build/provider";

async function openShell(
  leaseId: any,
  certificate: any,
  service: string,
  command: string[] = ["/bin/sh"]
) {
  const shell = await leaseShell(leaseId, certificate, service, command);

  // shell is a WebSocket-like interface
  shell.onmessage = (event) => {
    process.stdout.write(event.data);
  };

  process.stdin.on("data", (data) => {
    shell.send(data);
  });

  return shell;
}
```

## Provider Discovery

### Get Provider Info

```typescript
async function getProviderInfo(providerAddress: string) {
  const response = await fetch(
    `https://console-api.akash.network/v1/providers/${providerAddress}`
  );

  if (!response.ok) {
    throw new Error("Failed to fetch provider info");
  }

  return response.json();
}
```

### List Active Providers

```typescript
async function listProviders(filters?: {
  region?: string;
  hasGpu?: boolean;
}) {
  const params = new URLSearchParams();
  if (filters?.region) params.set("region", filters.region);
  if (filters?.hasGpu) params.set("hasGpu", "true");

  const response = await fetch(
    `https://console-api.akash.network/v1/providers?${params}`
  );

  return response.json();
}
```

## Complete Provider Interaction Flow

```typescript
import { SigningStargateClient } from "@cosmjs/stargate";
import { SDL } from "@akashnetwork/akashjs/build/sdl";
import { certificateManager } from "@akashnetwork/akashjs/build/certificates";
import { sendManifest, queryLeaseStatus } from "@akashnetwork/akashjs/build/provider";

class AkashDeployment {
  private client: SigningStargateClient;
  private address: string;
  private certificate: { cert: string; privateKey: string };

  constructor(
    client: SigningStargateClient,
    address: string,
    certificate: { cert: string; privateKey: string }
  ) {
    this.client = client;
    this.address = address;
    this.certificate = certificate;
  }

  async deploy(sdlContent: string) {
    const sdl = SDL.fromString(sdlContent);
    const dseq = Date.now().toString();

    // 1. Create deployment
    const deployTx = await this.createDeployment(sdl, dseq);
    console.log(`Deployment created: ${dseq}`);

    // 2. Wait for bids
    const bids = await this.waitForBids(dseq);
    if (bids.length === 0) {
      throw new Error("No bids received");
    }

    // 3. Select best bid
    const selectedBid = this.selectBid(bids);
    console.log(`Selected provider: ${selectedBid.provider}`);

    // 4. Create lease
    await this.createLease(dseq, selectedBid.provider);

    // 5. Send manifest
    const leaseId = {
      owner: this.address,
      dseq,
      gseq: 1,
      oseq: 1,
      provider: selectedBid.provider
    };

    await this.sendManifestWithRetry(leaseId, sdl.manifest());

    // 6. Wait for deployment to be ready
    const status = await this.waitForReady(leaseId);

    return {
      dseq,
      provider: selectedBid.provider,
      uris: this.extractUris(status)
    };
  }

  private async createDeployment(sdl: SDL, dseq: string) {
    const msg = {
      typeUrl: "/akash.deployment.v1beta3.MsgCreateDeployment",
      value: {
        id: { owner: this.address, dseq: BigInt(dseq) },
        groups: sdl.groups(),
        version: await sdl.manifestVersion(),
        deposit: { denom: "uact", amount: "5000000" },
        depositor: this.address
      }
    };

    return this.client.signAndBroadcast(this.address, [msg], "auto");
  }

  private async waitForBids(dseq: string, timeout = 60000): Promise<any[]> {
    const startTime = Date.now();

    while (Date.now() - startTime < timeout) {
      const response = await fetch(
        `https://console-api.akash.network/v1/bids/${dseq}`
      );
      const { data: bids } = await response.json();

      if (bids && bids.length > 0) {
        return bids;
      }

      await new Promise(r => setTimeout(r, 5000));
    }

    return [];
  }

  private selectBid(bids: any[]) {
    // Select lowest price bid
    return bids.sort((a, b) =>
      Number(a.price.amount) - Number(b.price.amount)
    )[0];
  }

  private async createLease(dseq: string, provider: string) {
    const msg = {
      typeUrl: "/akash.market.v1beta4.MsgCreateLease",
      value: {
        bidId: {
          owner: this.address,
          dseq: BigInt(dseq),
          gseq: 1,
          oseq: 1,
          provider
        }
      }
    };

    return this.client.signAndBroadcast(this.address, [msg], "auto");
  }

  private async sendManifestWithRetry(leaseId: any, manifest: any, retries = 3) {
    for (let i = 0; i < retries; i++) {
      try {
        await sendManifest(leaseId, manifest, this.certificate);
        return;
      } catch (error) {
        if (i === retries - 1) throw error;
        await new Promise(r => setTimeout(r, 2000 * (i + 1)));
      }
    }
  }

  private async waitForReady(leaseId: any, timeout = 120000) {
    const startTime = Date.now();

    while (Date.now() - startTime < timeout) {
      try {
        const status = await queryLeaseStatus(leaseId, this.certificate);

        const allReady = Object.values(status.services).every(
          (svc: any) => svc.available > 0
        );

        if (allReady) {
          return status;
        }
      } catch (error) {
        // Provider may not be ready yet
      }

      await new Promise(r => setTimeout(r, 5000));
    }

    throw new Error("Deployment timed out");
  }

  private extractUris(status: any): Record<string, string[]> {
    const uris: Record<string, string[]> = {};

    for (const [name, service] of Object.entries(status.services)) {
      uris[name] = (service as any).uris || [];
    }

    return uris;
  }
}
```

## Error Handling

```typescript
class ProviderError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly provider?: string
  ) {
    super(message);
    this.name = "ProviderError";
  }
}

function handleProviderError(error: unknown): never {
  if (error instanceof Error) {
    if (error.message.includes("certificate")) {
      throw new ProviderError(
        "Certificate error - regenerate certificate",
        "CERT_ERROR"
      );
    }

    if (error.message.includes("connection")) {
      throw new ProviderError(
        "Provider connection failed",
        "CONNECTION_ERROR"
      );
    }

    if (error.message.includes("manifest")) {
      throw new ProviderError(
        "Invalid manifest",
        "MANIFEST_ERROR"
      );
    }
  }

  throw new ProviderError(
    "Unknown provider error",
    "UNKNOWN_ERROR"
  );
}
```
