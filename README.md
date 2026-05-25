# Akash Network Plugin for Claude Code

A Claude Code **plugin** bundling three focused skills for the Akash Network — the decentralized cloud computing marketplace.

| Skill | Persona | What it covers |
|---|---|---|
| `akash-network:akash` | Deployer | SDL syntax, Console API (with API key), Akash CLI, TypeScript/Go SDKs, **AkashML managed inference** (OpenAI/Anthropic-compatible LLM APIs on Akash compute), authz, bid-matching, payment in `uact` / IBC denoms |
| `akash-network:akash-provider` | Provider operator | Kubernetes prereqs, provider installation, attributes & pricing, bid engine, monitoring, troubleshooting |
| `akash-network:akash-node` | Node / validator operator | Full node setup, state sync, validator setup, slashing avoidance, sentry nodes, key management |

The companion skill `akash-bid-matcher` (distributed separately) gives live bid-failure diagnostics against the current provider set and is referenced from `akash-network:akash`.

## Quick start

### Install via marketplace (recommended)

This repo publishes its own Claude Code plugin marketplace. From inside a Claude Code session:

```
/plugin marketplace add akash-network/akash-skill
/plugin install akash-network@akash-network
```

The first command registers the marketplace from this GitHub repo; the second installs the bundled plugin. To pin to a specific release instead of the default branch:

```
/plugin marketplace add akash-network/akash-skill@v3.0.0
```

Use `/plugin marketplace update akash-network` to pull new releases later.

### Try without installing (local clone)

Useful for development against an unreleased branch, or for trying the plugin in a single session without persisting it:

```bash
git clone https://github.com/akash-network/akash-skill
cd akash-skill
claude --plugin-dir "$(pwd)"
```

This loads the plugin **for the current session only**. Subsequent `claude` invocations won't see it — use the marketplace install above if you want persistence.

### Trigger the skills

Once installed, the skills auto-trigger on relevant queries. Examples:

- *"Deploy this SDL to Akash using my API key"* → `akash-network:akash`
- *"How do I call an LLM on Akash with the OpenAI SDK?"* → `akash-network:akash` (AkashML path)
- *"Set up an Akash provider on a Kubernetes cluster"* → `akash-network:akash-provider`
- *"How do I run an Akash validator with state sync?"* → `akash-network:akash-node`

You can also invoke them explicitly: `/akash-network:akash`, `/akash-network:akash-provider`, `/akash-network:akash-node`.

## Repo layout

```
.
├── .claude-plugin/
│   ├── plugin.json              # Plugin manifest (name, version, author)
│   └── marketplace.json         # Marketplace manifest (lists this plugin)
├── skills/
│   ├── akash/                   # Deployer skill
│   │   ├── SKILL.md
│   │   ├── rules/
│   │   │   ├── overview.md
│   │   │   ├── terminology.md
│   │   │   ├── pricing.md
│   │   │   ├── sdl/             # SDL syntax and examples
│   │   │   ├── deploy/
│   │   │   │   ├── overview.md  # Method selection
│   │   │   │   ├── console-api/ # Console API (API key path)
│   │   │   │   ├── cli/         # Akash CLI (self-custody)
│   │   │   │   ├── akashml/     # AkashML managed inference (consumption path)
│   │   │   │   └── certificates/
│   │   │   ├── sdk/
│   │   │   │   ├── typescript/  # @akashnetwork/chain-sdk
│   │   │   │   └── go/          # github.com/akash-network/akash-api
│   │   │   ├── authz/           # Fee grants & delegated permissions
│   │   │   ├── bid-matching/    # Deployer-facing bid explainers
│   │   │   └── reference/       # GPU models, storage classes, IBC denoms, RPC
│   │   └── scripts/
│   │       └── match_providers.py
│   ├── akash-provider/          # Provider operator skill
│   │   ├── SKILL.md
│   │   └── rules/
│   │       ├── requirements.md
│   │       ├── setup/           # Kubernetes, installation, config
│   │       ├── configuration/   # Attributes, pricing, bid engine
│   │       └── operations/      # Leases, monitoring, troubleshooting
│   └── akash-node/              # Node / validator skill
│       ├── SKILL.md
│       └── rules/
│           ├── overview.md
│           ├── full-node/       # Installation, requirements, state sync
│           └── validator/       # Becoming a validator, ops, security
├── SKILL.md                     # Deprecation stub for the old standalone skill
├── README.md                    # This file
└── LICENSE
```

## Upgrading from v2.x (standalone skill → plugin)

If you previously installed this repo as a single `akash` skill (e.g. by symlinking or cloning into `~/.claude/skills/akash/`):

1. **Remove the old install.** Delete the standalone skill directory:

   ```bash
   rm -rf ~/.claude/skills/akash
   ```

   (Adjust the path if you used a different location.)

2. **Install as a plugin via the marketplace** (from inside a Claude Code session):

   ```
   /plugin marketplace add akash-network/akash-skill
   /plugin install akash-network@akash-network
   ```

3. The three skills will now show up as `akash-network:akash`, `akash-network:akash-provider`, and `akash-network:akash-node`. The trigger phrases are the same as before; only the namespacing changed.

If you keep the old `~/.claude/skills/akash` install around, both will coexist (Claude Code uses different namespaces for plugin vs. standalone skills). Behaviour from the old standalone may be stale — remove it once the plugin is working.

## What changed in v3.0.0

This is a major restructure. Highlights:

- **Three skills instead of one.** Deployer, provider operator, and validator operator are distinct personas; each now has its own focused skill description.
- **AkashML managed inference.** New section [`skills/akash/rules/deploy/akashml/`](skills/akash/rules/deploy/akashml/) covering [playground.akashml.com](https://playground.akashml.com) — Akash's OpenAI- and Anthropic-compatible LLM API. Documented as a *consumption* path distinct from the four *deployment* paths: when a user wants to **call** an LLM (not host one), the skill now routes to AkashML instead of jumping straight to a GPU SDL. Includes a Claude Code integration guide for routing Claude Code itself through AkashML via `ANTHROPIC_BASE_URL`.
- **Console API documentation rebuilt against the live spec.** All endpoint paths, request bodies, and auth headers have been updated. Notably:
  - Authentication uses the `x-api-key` header. `Authorization: Bearer` is for JWTs only.
  - All paths are `/v1/...` and resource names are plural (e.g. `/v1/deployments`, not `/v1/deployment`).
  - Bodies wrap in `{ "data": { ... } }`.
  - `deposit` is a USD number, not a `"5000000uact"` string.
  - Leases are created in batch via `POST /v1/leases` (which also sends the manifest).
  - `/v1/sdl/validate` and `/v1/sdl/price` no longer exist; pricing is now `POST /v1/pricing` against raw `cpu/memory/storage` numbers.
  - `POST /v1/certificates` is removed for the Console API path — identity is verified by API key.
- **Method-selection guidance.** The deployer skill now asks once which deployment method (Console API, CLI, TypeScript SDK, Go SDK) the user wants and commits to it. The previous version conflated "Console API" with "managed wallet" and steered API-key users toward CLI/cert workflows.
- **Console Air disambiguation.** The new **self-hosted** Console Air repo (self-custody UI for Keplr or hardware wallets — clone from [github.com/akash-network/console-air](https://github.com/akash-network/console-air)) is called out distinctly from the managed-wallet `console.akash.network`.
- **Logs/events flow documented.** New file `skills/akash/rules/deploy/console-api/operations.md` covers the full JWT + provider proxy + WebSocket flow for streaming logs from a running deployment.
- **TypeScript SDK refreshed.** Documentation now targets `@akashnetwork/chain-sdk` (the current package); the deprecated `@akashnetwork/akashjs` has been removed entirely.
- **Denom rename.** All `uakt` references replaced with `uact` (the current native denom). The legacy name is only mentioned in historical / migration notes.
- **mTLS marked deprecated for Console API.** The CLI flow still uses certs where applicable; the Console API path no longer does.

## Contributing

Found something stale or wrong? Open an issue or PR at https://github.com/akash-network/akash-skill.

The skills are written for [Claude Code](https://docs.claude.com/) but should be readable as general Akash documentation as well.

## License

MIT — see `LICENSE`.

## Related projects

- [`akash-network/console`](https://github.com/akash-network/console) — Managed-wallet Console (UI + API)
- [`akash-network/console-air`](https://github.com/akash-network/console-air) — Self-custody Console
- [`akash-network/chain-sdk`](https://github.com/akash-network/chain-sdk) — TypeScript/Go/Rust SDKs
- [`akash-network/node`](https://github.com/akash-network/node) — Akash chain node
- [`akash-network/provider`](https://github.com/akash-network/provider) — Provider services
- [`akash-network/awesome-akash`](https://github.com/akash-network/awesome-akash) — Production-ready SDL templates
