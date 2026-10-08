# akt CLI

`akt` is the unified Akash command-line tool. It replaces the CLI work previously split across `akash`, `provider-services` and the chain SDK CLI, and deploys through either of two rails:

| Rail | Who signs and pays | Credential | Use it when |
|---|---|---|---|
| Console (`console-api`) | Console's managed wallet, from the account's USD credits | Console API key | The user has a Console account and no wallet to manage |
| Chain (`keyring`) | The user's own key, in ACT | Local keyring account | Self-custody |

One context can hold both credentials; its preference picks the rail for `akt deploy`, `akt update` and `akt close`. `akt console …` commands always use Console and `akt tx …` always signs locally.

Official docs: [akash.network/docs/developers/deployment/akt](https://akash.network/docs/developers/deployment/akt/). Source and releases: [github.com/akash-network/akt](https://github.com/akash-network/akt).

## When to use akt

- The user mentions akt, or `command -v akt` finds it, and wants something deployed or inspected from a terminal. Use akt rather than hand-written Console API calls or `provider-services`: one `akt deploy` creates the deployment, waits for bids, picks one, opens the lease, sends the manifest and waits for the service.
- Code that deploys on behalf of an application, or a pipeline that shouldn't install tools, is still better served by the Console API over HTTP: [../console-api/](../console-api/).
- akt has no sealed secrets (`sealedSecrets`, `ac-secret://`), no targeted `PATCH` and no `inheritSecretsFrom`. Those need the Console API.

## Install

```bash
brew tap akash-network/tap
brew install akash-network/tap/akt     # latest stable release
akt version
```

Homebrew ships stable releases only. Release candidates are archives on [GitHub Releases](https://github.com/akash-network/akt/releases) (a universal macOS zip, Linux amd64 and arm64 zips, `.deb` and `.rpm`); check them against the release's `akt_<version>_checksums.txt`. Full steps: [installation docs](https://akash.network/docs/developers/deployment/akt/installation/).

akt has its own agent skill, `akt-cli`, about driving the binary itself: every command family, context inspection, recovery. Get it from `https://akash.network/skills/akt-cli.zip` or the release's `akt_<version>_skill.zip`, and extract the whole `akt-cli/` folder into the agent's skills directory (`~/.claude/skills/` for Claude Code, `~/.agents/skills/` for Codex).

## Check the version first

Console-rail behavior changed between releases. Run `akt version` before giving commands:

| | akt 0.1.x (Homebrew stable) | akt 1.0 (release candidate) |
|---|---|---|
| Deposit on a Console deploy | Required: `--deposit 0.5` or more, in USD (`0.5`, `0.5usd`, `$0.50`). Console ignores the amount and funds the deployment itself | Refused: any deposit on the Console rail is an error, so pass none |
| `akt console deployment create` | Takes a USD deposit argument | No deposit argument |
| `akt console deployment settings <dseq>` | `true` or `false` toggles the old auto top-up | `<hours>` sets a runtime limit, `none` removes it |
| `akt console deployment deposit` | Calls an endpoint Console has deprecated; don't use it | Removed |
| `akt console screen --gpu-model` | Ignored, so every model returns the same providers | Filters by model |
| `akt sdl init --architecture` | Absent | `amd64` or `arm64` |

When an example here and the installed binary disagree, `akt <command> --help` wins.

## Set up a Console context

A context holds the network, keyring, Console credential, local deployment store and action log. In a terminal, the first `akt` run starts a setup wizard. Without a terminal (an agent's shell, CI) akt never prompts: it reports that no configuration exists and the command fails. Create the context explicitly:

```bash
akt context create ci --deploy-via console --set-current
```

`--deploy-via console` needs no network and no keyring. `akt deploy`, `update` and `close` refuse to run without a context, even when a key is available.

The API key resolves in this order: the `--console-api-key` flag, then `AKT_CONSOLE_API_KEY`, then the key stored with the context.

| Situation | Do this |
|---|---|
| CI, agents, anything non-interactive | Export `AKT_CONSOLE_API_KEY` from the secret store; nothing is written to disk |
| A person at a terminal | `akt console login` asks for the key with hidden input and stores it for the context (file mode 0600, never in `config.yaml`) |

Keep the key off the command line (`--console-api-key <key>`, `akt console login <key>`), where shell history and process listings keep it. Keys are created in Console under Settings → API Keys and start with `ac.sk.`.

Confirm before acting:

```bash
akt console whoami -o json
akt context show -o json      # auth_method, console_api_key_configured, capabilities
```

`capabilities.console: true` only means a key resolves; `whoami` proves it works. A Console-only context reports `chain_query`, `chain_tx` and `provider` as false, and commands that need them answer "unavailable" with the missing setting.

## Chain rail (self-custody)

```bash
akt context network list
akt context create mine --network mainnet --default-account alice --set-current
```

If the network isn't listed, add it with `akt context network create` (see its `--help`). The account must already exist in the context's keyring (`akt context keys --help`); creating or importing a key is a separate task that produces sensitive backup material. On this rail `akt deploy` defaults to `--deposit auto`, the chain minimum in the network's deposit denomination, and the wallet pays deposits and fees, so it needs ACT minted from AKT first ([../../pricing.md](../../pricing.md)). Chain queries, transactions and provider-gateway commands live under `akt query`, `akt tx` and `akt provider`.

## Machine-readable output

- Use `-o json` for reads and `-o jsonl` for `deploy`, `update` and `close`, which write one record per workflow step.
- Each JSONL record has `workflow`, `id`, `step`, `result` (`completed`, `skipped` or `error`), `errors` and `txs`, plus the step's `outputs`. The new dseq is in the `create-deployment` record: `jq -r 'select(.step=="create-deployment") | .outputs.dseq'`. A failed step can also carry `dseq`, `provider`, `recovery` and `cleanup`, the last two being commands to run next.
- Check the exit status too. `akt sdl validate` exits 0 when valid, 1 when invalid and 2 when it can't read the file.
- `akt sdl init` writes raw YAML: redirect it to a file and don't pass `-o`.
- Pretty output shows amounts in dollars. JSON keeps micro-denominations (`uact`), so convert before quoting a price.

## MCP server

`akt mcp` serves Akash tools over stdio: chain reads when the context has an RPC endpoint, and Console reads (deployments, bids, providers, GPU prices, balance, usage) when a Console key resolves. It starts read-only. `--enable-writes` adds closing deployments, creating and closing leases and submitting manifests, and needs an explicitly selected context so every mutation is logged.

The user stores the key once at a terminal, then registers the server:

```bash
akt console login --context ops
claude mcp add akt -- akt mcp --context ops
```

Add `--enable-writes` to the second command only if the user wants the agent to close deployments or create leases for them. JSON-configured clients use `{"command": "akt", "args": ["mcp", "--context", "ops"]}`.

## How akt maps to the Console API

akt calls the endpoints documented in [../console-api/](../console-api/), with two differences:

- `akt update` and `akt console deployment update` resubmit the whole SDL through `PUT /v1/deployments/{dseq}`, which the API has deprecated in favor of `PATCH`. It still works, but akt has no command for a targeted patch.
- `akt deploy` and `akt console lease create` still send a manifest to `POST /v1/leases`, which Console no longer needs.

Recipes for the Console rail: [console-workflows.md](console-workflows.md).
