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
    authtypes "github.com/cosmos/cosmos-sdk/x/auth/types"
    "google.golang.org/grpc"
    "google.golang.org/grpc/credentials/insecure"

    akashcodec "github.com/akash-network/akash-api/go/node/codec"
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

    // Create codec
    interfaceRegistry := codectypes.NewInterfaceRegistry()
    akashcodec.RegisterInterfaces(interfaceRegistry)
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
    grpcConn, err := grpc.Dial(
        nodeURI,
        grpc.WithTransportCredentials(insecure.NewCredentials()),
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
        WithGasPrices("0.025uact").
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

```go
import (
    deploymentv1beta3 "github.com/akash-network/akash-api/go/node/deployment/v1beta3"
)

func (c *AkashClient) CreateDeployment(
    ctx context.Context,
    dseq uint64,
    groups []deploymentv1beta3.GroupSpec,
    version []byte,
    deposit sdk.Coin,
) (*sdk.TxResponse, error) {
    msg := &deploymentv1beta3.MsgCreateDeployment{
        ID: deploymentv1beta3.DeploymentID{
            Owner: c.address.String(),
            DSeq:  dseq,
        },
        Groups:    groups,
        Version:   version,
        Deposit:   deposit,
        Depositor: c.address.String(),
    }

    return c.broadcastTx(ctx, msg)
}

func (c *AkashClient) CloseDeployment(
    ctx context.Context,
    dseq uint64,
) (*sdk.TxResponse, error) {
    msg := &deploymentv1beta3.MsgCloseDeployment{
        ID: deploymentv1beta3.DeploymentID{
            Owner: c.address.String(),
            DSeq:  dseq,
        },
    }

    return c.broadcastTx(ctx, msg)
}

func (c *AkashClient) DepositDeployment(
    ctx context.Context,
    dseq uint64,
    amount sdk.Coin,
) (*sdk.TxResponse, error) {
    msg := &deploymentv1beta3.MsgDepositDeployment{
        ID: deploymentv1beta3.DeploymentID{
            Owner: c.address.String(),
            DSeq:  dseq,
        },
        Amount:    amount,
        Depositor: c.address.String(),
    }

    return c.broadcastTx(ctx, msg)
}

func (c *AkashClient) QueryDeployment(
    ctx context.Context,
    dseq uint64,
) (*deploymentv1beta3.QueryDeploymentResponse, error) {
    queryClient := deploymentv1beta3.NewQueryClient(c.clientCtx.GRPCClient)

    return queryClient.Deployment(ctx, &deploymentv1beta3.QueryDeploymentRequest{
        ID: deploymentv1beta3.DeploymentID{
            Owner: c.address.String(),
            DSeq:  dseq,
        },
    })
}
```

## Market Operations

```go
import (
    marketv1beta4 "github.com/akash-network/akash-api/go/node/market/v1beta4"
)

func (c *AkashClient) CreateLease(
    ctx context.Context,
    dseq uint64,
    gseq uint32,
    oseq uint32,
    provider string,
) (*sdk.TxResponse, error) {
    msg := &marketv1beta4.MsgCreateLease{
        BidID: marketv1beta4.BidID{
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
) (*marketv1beta4.QueryBidsResponse, error) {
    queryClient := marketv1beta4.NewQueryClient(c.clientCtx.GRPCClient)

    return queryClient.Bids(ctx, &marketv1beta4.QueryBidsRequest{
        Filters: marketv1beta4.BidFilters{
            Owner: c.address.String(),
            DSeq:  dseq,
        },
    })
}

func (c *AkashClient) QueryLeases(
    ctx context.Context,
) (*marketv1beta4.QueryLeasesResponse, error) {
    queryClient := marketv1beta4.NewQueryClient(c.clientCtx.GRPCClient)

    return queryClient.Leases(ctx, &marketv1beta4.QueryLeasesRequest{
        Filters: marketv1beta4.LeaseFilters{
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
        "grpc.akashnet.net:443",
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

    txRes, err := client.CreateDeployment(ctx, dseq, groups, version, deposit)
    if err != nil {
        log.Fatal(err)
    }

    fmt.Printf("Deployment created: %s\n", txRes.TxHash)
}
```
