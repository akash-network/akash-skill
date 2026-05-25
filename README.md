# Akash Network Plugin for Claude Code

A Claude Code **plugin** bundling three focused skills for the Akash Network — the decentralized cloud computing marketplace.

| Skill | Persona | What it covers |
|---|---|---|
| `akash-network:akash` | Deployer | SDL syntax, Console API (with API key), Akash CLI, TypeScript/Go SDKs, **AkashML managed inference** (OpenAI/Anthropic-compatible LLM APIs on Akash compute), authz, bid-matching, payment in `uact` |
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
/plugin marketplace add akash-network/akash-skill@v3.0.1
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
│   │   │   └── reference/       # GPU models, storage classes, RPC endpoints
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
