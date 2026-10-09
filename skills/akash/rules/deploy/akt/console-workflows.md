# akt CLI: Console workflows

Recipes for a context that deploys through Console, written for akt 1.0.1 and later. Setup, credentials and what differs on 0.1.x are in [overview.md](overview.md). Examples use dseq `1234567` and service `web`; replace both, and add `--context <name>` when the work targets a context other than the current one.

## Write and check the SDL

```bash
akt sdl scaffolds                                  # web, gpu, multi-service, ip-lease
akt sdl init web --image nginx:1.27.3 --port 80 > deploy.yaml
akt sdl validate deploy.yaml -o json               # valid, errors, warnings
```

The `sdl` commands run offline and need no context. Validation rejects untagged and `:latest` images. Price in `uact` ([../../sdl/placement-pricing.md](../../sdl/placement-pricing.md)); `uakt` pricing doesn't work on the Console rail.

## Deploy

Preview the plan, then run it:

```bash
akt deploy deploy.yaml --dry-run -o jsonl
akt deploy deploy.yaml --bid-select cheapest --yes -o jsonl
```

- `--bid-select` decides the bid: `cheapest`, or `provider=<full akash1… address>` once a provider has been chosen. The default, `interactive`, waits for a person to pick, so an agent or a CI job always passes it. Choose `cheapest` only when any provider that satisfies the SDL is acceptable; region, audit and hardware requirements belong in the SDL's placement attributes.
- `--yes` skips confirmations. It doesn't choose a bid.
- `--bid-timeout` (default `5m`) bounds the wait for bids and `--ready-timeout` (default `2m`) the wait for the service. `--no-wait-active` returns as soon as the manifest is sent.
- Pass no deposit: 1.0.1 refuses one on Console. On 0.1.x, upgrade (`brew upgrade akash-network/tap/akt`); if that isn't possible, add `--deposit 0.5`.
- The run prints the dseq. With `-o jsonl`, read it from the `create-deployment` record's `outputs.dseq`.

To look at the bids before choosing, run the steps separately: `akt console deployment create deploy.yaml`, then `akt console bid list 1234567 -o json`, then `akt console lease create 1234567 <provider-address>`.

## Secrets

Reference a secret as the whole value of an env entry, or of a registry `credentials` `username` or `password`, and keep the values in a separate JSON or YAML map:

```yaml
# deploy.yaml
    env:
      - "LOG_LEVEL=info"
      - "DATABASE_URL=ac-secret://DATABASE_URL"
```

```yaml
# secrets.yaml, kept out of version control
DATABASE_URL: "postgres://app:<password>@db.internal:5432/app"
```

```bash
akt deploy deploy.yaml --secrets-file secrets.yaml --bid-select cheapest --yes -o jsonl
# or build the map from the environment, so it never touches disk
jq -n '{DATABASE_URL: env.DATABASE_URL}' | akt deploy deploy.yaml --secrets-file - --bid-select cheapest --yes -o jsonl
```

- `--secrets-file -` reads the map from stdin. Never put a value in a flag, a `jq --arg` or the SDL, where shell history and process listings keep it.
- Names are letters, digits and `_`, start with a letter or `_`, and run up to 64 characters. Every reference needs a value, supplied or (on redeploy) inherited, or Console answers 400: [../console-api/secrets.md](../console-api/secrets.md).
- Plain variables stay readable in the saved SDL. `akt console deployment sdl 1234567` prints the saved SDL with every secret still a reference, and no command reads a value back.
- Secrets need a Console context; the chain rail rejects `ac-secret://` and `--secrets-file`.

## Inspect

```bash
akt console deployment list active -o json         # or closed; --limit, --skip
akt console deployment get 1234567 -o json         # Console's record: leases, escrow
akt console status 1234567 -o json                 # live from the provider: services, forwarded ports, IPs
akt console logs 1234567 web --tail 50             # no service = all services; --follow streams
akt console events 1234567 -o json                 # Kubernetes events; --follow streams
akt console shell 1234567 web -- ls -la /app       # one command; -o json captures stdout and stderr
```

Logs, events, status and shell go straight to the provider with a short-lived JWT that Console mints; no wallet or certificate is involved. The service is positional (`logs 1234567 web`), not a `--service` flag. Without `--`, `shell` opens an interactive session an agent can't drive, so always give it a command.

## Update

Edit the SDL, validate it, then pass the SDL first and the dseq second. When the original file isn't at hand, start from Console's saved copy:

```bash
akt console deployment sdl 1234567 > deploy.yaml   # secrets come back as references
akt sdl validate deploy.yaml
akt update deploy.yaml 1234567 --dry-run -o jsonl
akt update deploy.yaml 1234567 --yes -o jsonl
```

akt compares the file with Console's saved SDL and sends only the difference, on the existing lease. Secrets the file still references keep their stored values. To add or replace one, reference it and pass its value with `--secrets-file`; to remove one, drop its reference.

For a small change, a patch file names only the fields to change:

```yaml
# changes.yaml
services:
  web:
    image: nginx:1.27.4
    env:
      LOG_LEVEL: debug
      OLD_FLAG: null
```

```bash
akt update changes.yaml 1234567 --patch --yes -o jsonl
akt update empty.yaml 1234567 --patch --secrets-file rotated.yaml --yes -o jsonl   # rotate values only; empty.yaml is `{}`
```

- A patch can change `image`, `command`, `args`, `env` (a map here, not the SDL's list), registry `credentials`, existing exposed ports and storage mounts. `null` removes a variable or clears `command`, `args` or `credentials`.
- Groups, compute resources, replica counts, placement, and the kind or number of exposed endpoints can't change in place. akt refuses them before sending anything; use `akt redeploy` below. akt's help text about reopening bids describes the chain rail.
- A version conflict means the deployment changed since akt read it. Fetch the SDL again and review it before retrying.
- `akt console deployment update` takes the arguments the other way round (`<dseq> <file>`) and accepts the same `--patch` and `--secrets-file`.

## Redeploy

```bash
akt redeploy 1234567 --bid-select cheapest --yes -o jsonl
akt redeploy 1234567 --sdl-file bigger.yaml --bid-select cheapest --yes -o jsonl
```

Redeploy creates a new deployment from the source's saved SDL, or from `--sdl-file`, and carries over its stored secrets; `--secrets-file` overrides individual values. The source can already be closed. If it isn't, redeploy leaves it running, so the user pays for both until it's closed. Read the new dseq from the `create-deployment` record, check the new deployment serves, and close the source only if the user asked for that.

## Funding and runtime

Console funds every deployment from the account's credits, so there is nothing to top up.

```bash
akt console wallet balance -o json                 # available, escrow and total, in USD
akt console deployment settings 1234567            # the deployment's funding record
akt console deployment settings 1234567 24         # set a 24-hour runtime limit; `none` removes it
```

On 0.1.x, `settings` toggles the retired auto top-up instead, and `akt console deployment deposit` calls a deprecated endpoint. Skip both. The runtime-limit rules (how far one request can extend it, the maximum) are in [../console-api/deployment-endpoints.md](../console-api/deployment-endpoints.md).

## Close

```bash
akt close 1234567 --dry-run -o jsonl
akt close 1234567 --yes -o jsonl
```

Closing is irreversible: the workload and its data are gone and the dseq can't be reused. Make sure the dseq is one the user asked to end, then confirm with `akt console deployment get 1234567`.

## Find capacity first

```bash
akt console screen deploy.yaml -o json             # providers that could bid on this SDL
akt console screen --cpu 4 --memory 16Gi --gpu 1 --gpu-model h100 -o json
akt console gpu -o json                            # GPU availability and prices
akt console provider list -o json                  # provider catalog; also get, regions, auditors
```

These read public data and need no API key.

## When something fails

- Read the error record in the JSONL: `recovery` and `cleanup` hold the commands to run next, and `dseq` and `provider` show what already exists.
- Console can commit a create or a lease and still time out. Don't rerun `akt deploy`. Check `akt console deployment get` and `akt console bid list`, then finish the missing step (`akt console lease create`) or close what was created.
- A lease error saying the manifest wasn't delivered means the lease exists and is being paid for: retry the same `akt console lease create`, or close the deployment. A provider that couldn't be reached before the lease means choosing another bid.
- An update whose outcome is unknown may already be saved on Console. Check `akt console deployment get`, then rerun the identical `akt update` without editing the file in between.
- `akt context log --type workflow -o json` lists recent runs, and `--workflow-id <id>` shows every step of one.
- Console's read is the authority. `akt store status` only shows akt's local record.

## CI

```bash
# AKT_CONSOLE_API_KEY comes from the CI secret store
akt context create ci --deploy-via console --set-current
akt sdl validate deploy.yaml
akt deploy deploy.yaml --bid-select cheapest --yes -o jsonl > deploy.jsonl
dseq=$(jq -r 'select(.step=="create-deployment") | .outputs.dseq' deploy.jsonl)
```

When the SDL references secrets, map them from the CI secret store into the step's `env` too and pipe them in: `jq -n '{DATABASE_URL: env.DATABASE_URL}' | akt deploy deploy.yaml --secrets-file - …`. In GitHub Actions, map the secrets into the step's `env` and append `dseq=$dseq` to `$GITHUB_OUTPUT` for later steps. Install a pinned akt, 1.0.1 or later, in the job (release archive or Homebrew), since the deposit flag and secrets depend on the version.
