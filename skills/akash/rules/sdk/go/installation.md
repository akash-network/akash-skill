# Go SDK Installation

Install and configure the Akash Go SDK for backend services.

## Packages

```go
// Akash API types and clients
import "github.com/akash-network/akash-api/go/node/deployment/v1beta3"
import "github.com/akash-network/akash-api/go/node/market/v1beta4"

// Cosmos SDK for client operations
import "github.com/cosmos/cosmos-sdk/client"
import "github.com/cosmos/cosmos-sdk/crypto/keyring"
```

## Installation

```bash
go get github.com/akash-network/akash-api@latest
go get github.com/cosmos/cosmos-sdk@v0.47.x
```

## Basic Setup

```go
package main

import (
    "context"
    "fmt"

    "github.com/cosmos/cosmos-sdk/client"
    "github.com/cosmos/cosmos-sdk/client/tx"
    "github.com/cosmos/cosmos-sdk/codec"
    "github.com/cosmos/cosmos-sdk/crypto/keyring"
    sdk "github.com/cosmos/cosmos-sdk/types"

    deploymentv1beta3 "github.com/akash-network/akash-api/go/node/deployment/v1beta3"
)

func main() {
    // Configure SDK
    config := sdk.GetConfig()
    config.SetBech32PrefixForAccount("akash", "akashpub")
    config.Seal()

    // Create client context
    clientCtx := client.Context{}.
        WithChainID("akashnet-2").
        WithNodeURI("https://rpc.akashnet.net:443")

    fmt.Println("Akash Go SDK ready")
}
```

## Configuration

### Client Context

```go
import (
    "github.com/cosmos/cosmos-sdk/client"
    "github.com/cosmos/cosmos-sdk/client/flags"
    "github.com/cosmos/cosmos-sdk/codec"
    codectypes "github.com/cosmos/cosmos-sdk/codec/types"
    "google.golang.org/grpc"
)

func createClientContext() (client.Context, error) {
    // Create codec
    interfaceRegistry := codectypes.NewInterfaceRegistry()
    cdc := codec.NewProtoCodec(interfaceRegistry)

    // Create gRPC connection
    grpcConn, err := grpc.Dial(
        "grpc.akashnet.net:443",
        grpc.WithInsecure(),
    )
    if err != nil {
        return client.Context{}, err
    }

    clientCtx := client.Context{}.
        WithChainID("akashnet-2").
        WithCodec(cdc).
        WithInterfaceRegistry(interfaceRegistry).
        WithGRPCClient(grpcConn)

    return clientCtx, nil
}
```

### Keyring Setup

```go
import (
    "github.com/cosmos/cosmos-sdk/crypto/keyring"
)

func setupKeyring(homeDir string) (keyring.Keyring, error) {
    kr, err := keyring.New(
        "akash",
        keyring.BackendFile,
        homeDir,
        nil,
        cdc,
    )
    if err != nil {
        return nil, err
    }

    return kr, nil
}
```

## Query Examples

### Query Deployment

```go
import (
    "context"

    deploymentv1beta3 "github.com/akash-network/akash-api/go/node/deployment/v1beta3"
)

func queryDeployment(
    ctx context.Context,
    clientCtx client.Context,
    owner string,
    dseq uint64,
) (*deploymentv1beta3.QueryDeploymentResponse, error) {
    queryClient := deploymentv1beta3.NewQueryClient(clientCtx.GRPCClient)

    return queryClient.Deployment(ctx, &deploymentv1beta3.QueryDeploymentRequest{
        Id: deploymentv1beta3.DeploymentID{
            Owner: owner,
            DSeq:  dseq,
        },
    })
}
```

### Query Leases

```go
import (
    marketv1beta4 "github.com/akash-network/akash-api/go/node/market/v1beta4"
)

func queryLeases(
    ctx context.Context,
    clientCtx client.Context,
    owner string,
) (*marketv1beta4.QueryLeasesResponse, error) {
    queryClient := marketv1beta4.NewQueryClient(clientCtx.GRPCClient)

    return queryClient.Leases(ctx, &marketv1beta4.QueryLeasesRequest{
        Filters: marketv1beta4.LeaseFilters{
            Owner: owner,
            State: "active",
        },
    })
}
```

## Transaction Examples

### Create Deployment

```go
import (
    "github.com/cosmos/cosmos-sdk/client/tx"
    sdk "github.com/cosmos/cosmos-sdk/types"

    deploymentv1beta3 "github.com/akash-network/akash-api/go/node/deployment/v1beta3"
)

func createDeployment(
    clientCtx client.Context,
    owner string,
    dseq uint64,
    deposit sdk.Coin,
) error {
    msg := &deploymentv1beta3.MsgCreateDeployment{
        ID: deploymentv1beta3.DeploymentID{
            Owner: owner,
            DSeq:  dseq,
        },
        Groups:    []deploymentv1beta3.GroupSpec{}, // Add your groups
        Version:   []byte{},
        Deposit:   deposit,
        Depositor: owner,
    }

    txf := tx.Factory{}.
        WithChainID(clientCtx.ChainID).
        WithGas(200000).
        WithGasAdjustment(1.5).
        WithGasPrices("0.025uakt")

    return tx.GenerateOrBroadcastTxWithFactory(clientCtx, txf, msg)
}
```

## Error Handling

```go
import (
    "google.golang.org/grpc/codes"
    "google.golang.org/grpc/status"
)

func handleQueryError(err error) error {
    if err == nil {
        return nil
    }

    st, ok := status.FromError(err)
    if !ok {
        return fmt.Errorf("unknown error: %w", err)
    }

    switch st.Code() {
    case codes.NotFound:
        return fmt.Errorf("resource not found")
    case codes.PermissionDenied:
        return fmt.Errorf("permission denied")
    case codes.Unavailable:
        return fmt.Errorf("service unavailable")
    default:
        return fmt.Errorf("grpc error: %s", st.Message())
    }
}
```

## Next Steps

- **@client-setup.md** - Complete client configuration
- **@examples/** - Full working examples
