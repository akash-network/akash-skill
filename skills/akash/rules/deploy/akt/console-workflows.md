# akt CLI: Console workflows

Recipes for a context that deploys through Console. Setup, credentials and the 0.1.x versus 1.0 differences are in [overview.md](overview.md). Examples use dseq `1234567` and service `web`; replace both, and add `--context <name>` when the work targets a context other than the current one.

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
- On akt 0.1.x add `--deposit 0.5`. On 1.0 pass no deposit at all.
- The run prints the dseq. With `-o jsonl`, read it from the `create-deployment` record's `outputs.dseq`.

To look at the bids before choosing, run the steps separately: `akt console deployment create deploy.yaml` (0.1.x wants a USD amount after the file), then `akt console bid list 1234567 -o json`, then `akt console lease create 1234567 <provider-address>`.

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

Edit the SDL, validate it, then pass the SDL first and the dseq second:

```bash
akt sdl validate deploy.yaml
akt update deploy.yaml 1234567 --dry-run -o jsonl
akt update deploy.yaml 1234567 --yes -o jsonl
```

Image, env and command changes go through on the existing lease. Console refuses an SDL that changes the groups, compute resources, replica counts or globally exposed ports (422, `deployment_resources_changed`), so those take a new deployment; akt's help text about reopening bids describes the chain rail. `akt console deployment update` takes the arguments the other way round (`<dseq> <sdl>`). akt sends the whole SDL every time; for sealed secrets or a one-field change, the Console API's `PATCH` is the tool ([../console-api/deployment-endpoints.md](../console-api/deployment-endpoints.md)).

## Funding and runtime

Console funds every deployment from the account's credits, so there is nothing to top up.

```bash
akt console wallet balance -o json                 # available, escrow and total, in USD
akt console deployment settings 1234567            # the deployment's funding record
akt console deployment settings 1234567 24         # 1.0: set a 24-hour runtime limit; `none` removes it
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

In GitHub Actions, map the secret into the step's `env` as `AKT_CONSOLE_API_KEY` and append `dseq=$dseq` to `$GITHUB_OUTPUT` for later steps. Install a pinned akt version in the job (release archive or Homebrew), since the deposit flag depends on it.
