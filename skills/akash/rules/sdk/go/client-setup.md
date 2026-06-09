# Go SDK Client Setup

Complete client configuration for Akash Go SDK.

## Full Client Setup

```go
package akash

import (
    "context"
    "fmt"
    "os"

    "github.com/cosmos/cosmos-sdk/client"
    "github.com/cosmos/cosmos-sdk/client/flags"
    "github.com/cosmos/cosmos-sdk/client/tx"
    "github.com/cosmos/cosmos-sdk/codec"
    codectypes "github.com/cosmos/cosmos-sdk/codec/types"
    "github.com/cosmos/cosmos-sdk/crypto/hd"
    "github.com/cosmos/cosmos-sdk/crypto/keyring"
    sdk "github.com/cosmos/cosmos-sdk/types"
    "github.com/cosmos/cosmos-sdk/types/tx/signing"
    authtypes "github.com/cosmos/cosmos-sdk/x/auth/types"
    "google.golang.org/grpc"
    "google.golang.org/grpc/credentials"

    // Codec registration is per-module in pkg.akt.dev/go (there is no
    // aggregate "node/codec" package). Each module exposes its own
    // RegisterInterfaces(registry). Verify exports at:
    // https://pkg.go.dev/pkg.akt.dev/go
    certv1 "pkg.akt.dev/go/node/cert/v1"
    deploymentv1beta4 "pkg.akt.dev/go/node/deployment/v1beta4"
    marketv1beta5 "pkg.akt.dev/go/node/market/v1beta5"
)

type AkashClient struct {
    clientCtx client.Context
    txFactory tx.Factory
    keyring   keyring.Keyring
    address   sdk.AccAddress
}

func NewAkashClient(
    nodeURI string,
    chainID string,
    keyringBackend string,
    keyringDir string,
    keyName string,
) (*AkashClient, error) {
    // Configure SDK
    config := sdk.GetConfig()
    config.SetBech32PrefixForAccount("akash", "akashpub")
    config.Seal()

    // Create codec — register each Akash module's interfaces individually
    // (no single aggregate registration helper exists).
    interfaceRegistry := codectypes.NewInterfaceRegistry()
    deploymentv1beta4.RegisterInterfaces(interfaceRegistry)
    marketv1beta5.RegisterInterfaces(interfaceRegistry)
    certv1.RegisterInterfaces(interfaceRegistry)
    cdc := codec.NewProtoCodec(interfaceRegistry)

    // Setup keyring
    kr, err := keyring.New(
        "akash",
        keyringBackend,
        keyringDir,
        os.Stdin,
        cdc,
    )
    if err != nil {
        return nil, fmt.Errorf("failed to create keyring: %w", err)
    }

    // Get key
    keyInfo, err := kr.Key(keyName)
    if err != nil {
        return nil, fmt.Errorf("failed to get key: %w", err)
    }

    address, err := keyInfo.GetAddress()
    if err != nil {
        return nil, fmt.Errorf("failed to get address: %w", err)
    }

    // Create gRPC connection
    grpcConn, err := grpc.NewClient(
        nodeURI,
        // Public mainnet gRPC is TLS on :443 — use TLS creds (system roots), not insecure.
        grpc.WithTransportCredentials(credentials.NewClientTLSFromCert(nil, "")),
    )
    if err != nil {
        return nil, fmt.Errorf("failed to connect to node: %w", err)
    }

    // Create client context
    clientCtx := client.Context{}.
        WithChainID(chainID).
        WithCodec(cdc).
        WithInterfaceRegistry(interfaceRegistry).
        WithTxConfig(tx.NewTxConfig(cdc, tx.DefaultSignModes)).
        WithAccountRetriever(authtypes.AccountRetriever{}).
        WithBroadcastMode(flags.BroadcastSync).
        WithKeyring(kr).
        WithFromName(keyName).
        WithFromAddress(address).
        WithGRPCClient(grpcConn)

    // Create tx factory
    txFactory := tx.Factory{}.
        WithChainID(chainID).
        WithKeybase(kr).
        WithGas(200000).
        WithGasAdjustment(1.5).
        WithGasPrices("0.025uakt").
        WithSignMode(signing.SignMode_SIGN_MODE_DIRECT)

    return &AkashClient{
        clientCtx: clientCtx,
        txFactory: txFactory,
        keyring:   kr,
        address:   address,
    }, nil
}

func (c *AkashClient) Address() string {
    return c.address.String()
}

func (c *AkashClient) Close() error {
    if c.clientCtx.GRPCClient != nil {
        return c.clientCtx.GRPCClient.Close()
    }
    return nil
}
```

## Deployment Operations

In `pkg.akt.dev/go` v0.2.14 the message/ID types span several packages: the
deployment messages live in `deployment/v1beta4`, but `DeploymentID` (and the
`Deployment`/`DeploymentReclamation` types) live in `deployment/v1`, and the
`Deposit` value type lives in `types/deposit/v1`. Verify every symbol below at
<https://pkg.go.dev/pkg.akt.dev/go>.

```go
import (
    deploymentv1 "pkg.akt.dev/go/node/deployment/v1"
    deploymentv1beta4 "pkg.akt.dev/go/node/deployment/v1beta4"
    depositv1 "pkg.akt.dev/go/node/types/deposit/v1"
)

func (c *AkashClient) CreateDeployment(
    ctx context.Context,
    dseq uint64,
    groups deploymentv1beta4.GroupSpecs,
    hash []byte,
    amount sdk.Coin,
) (*sdk.TxResponse, error) {
    // MsgCreateDeployment v1beta4 fields are ID/Groups/Hash/Deposit/Reclamation.
    // There is no Version or Depositor field, and Deposit is a deposit/v1.Deposit
    // (which wraps the sdk.Coin), not a bare sdk.Coin.
    msg := &deploymentv1beta4.MsgCreateDeployment{
        ID: deploymentv1.DeploymentID{
            Owner: c.address.String(),
            DSeq:  dseq,
        },
        Groups: groups,
        Hash:   hash,
        Deposit: depositv1.Deposit{
            Amount: amount,
        },
    }

    return c.broadcastTx(ctx, msg)
}

func (c *AkashClient) CloseDeployment(
    ctx context.Context,
    dseq uint64,
) (*sdk.TxResponse, error) {
    msg := &deploymentv1beta4.MsgCloseDeployment{
        ID: deploymentv1.DeploymentID{
            Owner: c.address.String(),
            DSeq:  dseq,
        },
    }

    return c.broadcastTx(ctx, msg)
}

// NOTE: MsgDepositDeployment was removed in deployment/v1beta4 (it only exists
// in the older v1beta3). To add funds to an existing deployment's escrow
// account on current chains, deposit via the escrow module / `provider-services
// tx deployment deposit` rather than a deployment Msg. Check the current
// message set at https://pkg.go.dev/pkg.akt.dev/go before relying on this.

func (c *AkashClient) QueryDeployment(
    ctx context.Context,
    dseq uint64,
) (*deploymentv1beta4.QueryDeploymentResponse, error) {
    queryClient := deploymentv1beta4.NewQueryClient(c.clientCtx.GRPCClient)

    return queryClient.Deployment(ctx, &deploymentv1beta4.QueryDeploymentRequest{
        ID: deploymentv1.DeploymentID{
            Owner: c.address.String(),
            DSeq:  dseq,
        },
    })
}
```

### Resource reclamation field (v2.1.0+)

The `Reclamation` field on `MsgCreateDeployment` (a `deploymentv1.DeploymentReclamation`)
is the AEP-82 minimum grace window — see **@../../sdl/reclamation.md** for what it
means. Leave it nil to keep pre-2.1 behavior; populate it (`MinWindow`, a
`time.Duration` within the governance bounds 1h–720h) to require a reclamation
window. The field is ignored by pre-2.1.0 nodes, so gate on discovery
(`node_version >= 2.1.0`) before relying on it — see below.

## Market Operations

As with deployments, the market `Msg`/query types live in `market/v1beta5` while
the `BidID` identifier lives in `market/v1`. Verify at
<https://pkg.go.dev/pkg.akt.dev/go>.

`MsgLeaseStartReclaim` (provider-signed; starts reclamation on an `Active` lease)
also lives in `pkg.akt.dev/go/node/market/v1beta5`, with `LeaseID` in
`pkg.akt.dev/go/node/market/v1`. Tenants do not send it; resume a paused group with
`MsgStartGroup` from `pkg.akt.dev/go/node/deployment/v1beta4`.

```go
import (
    marketv1 "pkg.akt.dev/go/node/market/v1"
    marketv1beta5 "pkg.akt.dev/go/node/market/v1beta5"
)

func (c *AkashClient) CreateLease(
    ctx context.Context,
    dseq uint64,
    gseq uint32,
    oseq uint32,
    provider string,
) (*sdk.TxResponse, error) {
    msg := &marketv1beta5.MsgCreateLease{
        BidID: marketv1.BidID{
            Owner:    c.address.String(),
            DSeq:     dseq,
            GSeq:     gseq,
            OSeq:     oseq,
            Provider: provider,
        },
    }

    return c.broadcastTx(ctx, msg)
}

func (c *AkashClient) QueryBids(
    ctx context.Context,
    dseq uint64,
) (*marketv1beta5.QueryBidsResponse, error) {
    queryClient := marketv1beta5.NewQueryClient(c.clientCtx.GRPCClient)

    return queryClient.Bids(ctx, &marketv1beta5.QueryBidsRequest{
        Filters: marketv1beta5.BidFilters{
            Owner: c.address.String(),
            DSeq:  dseq,
        },
    })
}

func (c *AkashClient) QueryLeases(
    ctx context.Context,
) (*marketv1beta5.QueryLeasesResponse, error) {
    queryClient := marketv1beta5.NewQueryClient(c.clientCtx.GRPCClient)

    return queryClient.Leases(ctx, &marketv1beta5.QueryLeasesRequest{
        Filters: marketv1.LeaseFilters{
            Owner: c.address.String(),
        },
    })
}
```

## Transaction Broadcasting

```go
func (c *AkashClient) broadcastTx(
    ctx context.Context,
    msgs ...sdk.Msg,
) (*sdk.TxResponse, error) {
    // Build unsigned tx
    txBuilder, err := tx.BuildUnsignedTx(c.txFactory, msgs...)
    if err != nil {
        return nil, fmt.Errorf("failed to build tx: %w", err)
    }

    // Sign tx
    err = tx.Sign(c.txFactory, c.clientCtx.FromName, txBuilder, true)
    if err != nil {
        return nil, fmt.Errorf("failed to sign tx: %w", err)
    }

    // Encode tx
    txBytes, err := c.clientCtx.TxConfig.TxEncoder()(txBuilder.GetTx())
    if err != nil {
        return nil, fmt.Errorf("failed to encode tx: %w", err)
    }

    // Broadcast
    res, err := c.clientCtx.BroadcastTx(txBytes)
    if err != nil {
        return nil, fmt.Errorf("failed to broadcast tx: %w", err)
    }

    if res.Code != 0 {
        return res, fmt.Errorf("tx failed: %s", res.RawLog)
    }

    return res, nil
}
```

## Usage Example

```go
func main() {
    client, err := NewAkashClient(
        "akash-grpc.publicnode.com:443",
        "akashnet-2",
        "file",
        os.ExpandEnv("$HOME/.akash"),
        "wallet",
    )
    if err != nil {
        log.Fatal(err)
    }
    defer client.Close()

    ctx := context.Background()

    // Create deployment
    dseq := uint64(time.Now().Unix())
    deposit := sdk.NewCoin("uact", sdk.NewInt(5000000))

    // groups is a deploymentv1beta4.GroupSpecs built from your SDL; hash is the
    // manifest version hash (sha256 of the manifest).
    txRes, err := client.CreateDeployment(ctx, dseq, groups, hash, deposit)
    if err != nil {
        log.Fatal(err)
    }

    fmt.Printf("Deployment created: %s\n", txRes.TxHash)
}
```
