# console-axi (CLI for the Console API)

`console-axi` is an ergonomic CLI over the same Console managed-wallet API this
method documents (`@overview.md`). Prefer it over hand-rolled `curl` when the user
wants a CLI, token-efficient output, or a one-shot deploy: it emits
[TOON](https://www.npmjs.com/package/@toon-format/toon), uses stable exit codes,
and every result carries a `help[]` block naming the next step. The managed wallet
signs server-side, so no private keys are handled. All money is USD.

## Install

```
curl -fsSL https://raw.githubusercontent.com/baktun14/console-axi/main/install.sh | sh
```

Self-contained binary (no Node required; macOS/Linux, arm64/x64). Update with
`console-axi upgrade`, remove with `console-axi uninstall`.

## Auth

Same API-key model as `@authentication.md` (`x-api-key`).

```
console-axi login --with-key <key>     # or: export CONSOLE_API_KEY=<key>
console-axi whoami
```

## Deploy in one command

```
console-axi deploy --sdl app.yml --deposit 5
```

Creates the deployment, waits for bids, accepts the cheapest, creates the lease,
waits until the workload is ready, and prints the live service URIs — one call.
On failure it leaves the deployment OPEN and prints the exact retry/close command.
Flags: `--accept cheapest|first|<provider>`, `--bid-timeout <s>`, `--timeout <s>`.

Atomic equivalents (mapping to `@deployment-endpoints.md`):

```
console-axi deployment create --sdl app.yml --deposit 5
console-axi bid list --dseq <dseq>
console-axi lease create --dseq <dseq> --gseq 1 --oseq 1 --provider <addr> --manifest
```

## Manage deployments

```
console-axi deployment list
console-axi deployment status <dseq>     # live readiness, URIs, forwarded ports
console-axi deployment view <dseq>       # state, escrow (USD), leases
console-axi deployment deposit <dseq> --amount 5
console-axi deployment close <dseq>      # idempotent
```

## Debug a running workload

Mirrors `@operations.md` (logs, events, shell) over the provider proxy:

```
console-axi logs <dseq> --tail 100 [--follow] [--service <svc>]
console-axi events <dseq> [--follow]
console-axi exec <dseq> --service web -- <cmd...>   # captures stdout/stderr + exit code
console-axi shell <dseq> --service web              # interactive TTY
```

## Wallet & funding

Mirrors `@account-and-funding.md` (all USD):

```
console-axi wallet balance                          # available / in-deployments / total
console-axi wallet settings --auto-reload true      # headless way to add funds
console-axi usage [--from <YYYY-MM-DD>] [--to <YYYY-MM-DD>]
```

## Keys & tokens

```
console-axi apikey list | create --name <n> | delete <id>
console-axi jwt create --ttl 300 --scope logs,shell
```

## Output & exit codes

TOON on stdout. Exit codes: 0 = success or idempotent no-op, 1 = error, 2 = usage.
Errors are structured (`error: { code, exit, message }`) with a `help[]` block.

> SDL authoring/pricing/bid-screening (`sdl init|validate|estimate|screen`,
> `deploy --skip-screening`) are landing in console-axi; add a "Building & screening
> an SDL" section here once released so this maps 1:1 to the pricing and
> bid-screening endpoints in `@deployment-endpoints.md`.
