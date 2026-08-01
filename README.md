# Akash Network Skills for Coding Agents

A portable skill bundle for Claude Code, Codex, OpenCode, and other coding agents. It provides three focused skills for the Akash Network — the decentralized cloud computing marketplace.

| Skill | Persona | What it covers |
|---|---|---|
| `akash-network:akash` | Deployer | SDL syntax, Console API (with API key), Akash CLI, TypeScript/Go SDKs, **AkashML managed inference** (OpenAI/Anthropic-compatible LLM APIs on Akash compute), authz, bid-matching, payment in `uact` |
| `akash-network:akash-provider` | Provider operator | Kubernetes prereqs, provider installation, attributes & pricing, bid engine, monitoring, troubleshooting |
| `akash-network:akash-node` | Node / validator operator | Full node setup, state sync, validator setup, slashing avoidance, sentry nodes, key management |

## Quick start

### Install in Claude Code via marketplace

This repo publishes its own Claude Code plugin marketplace. From inside a Claude Code session:

```
/plugin marketplace add akash-network/akash-skill
/plugin install akash-network@akash-network
```

The first command registers the marketplace from this GitHub repo; the second installs the bundled plugin. To pin to a specific release instead of the default branch:

```
/plugin marketplace add akash-network/akash-skill@v3.0.2
```

Use `/plugin marketplace update akash-network` to pull new releases later.

### Install in Codex

Codex reads the plugin manifest at `.codex-plugin/plugin.json` and loads the three skills from `skills/`.

For local development, install this repository as a local Codex plugin from the Codex plugin UI or any Codex marketplace entry that points at this repo. The plugin manifest declares:

- `skills: "./skills/"` — loads `akash`, `akash-provider`, and `akash-node`
- `interface.displayName: "Akash Network"` — display name in Codex plugin surfaces
- `interface.defaultPrompt` — starter prompts for common Akash tasks

### Use with OpenCode and generic coding agents

OpenCode discovers project skills from `.agents/skills/<name>/SKILL.md`, among other paths. This repo exposes `.agents/skills` as a symlink to the canonical `skills/` directory, so OpenCode and other agent-compatible clients can load the same three skills without duplicated content.

From this repository, start OpenCode or another compatible agent with the repo as the working directory. The skills are available as:

- `akash`
- `akash-provider`
- `akash-node`

For a global install, link each canonical skill into your agent-compatible skills directory:

```bash
mkdir -p ~/.agents/skills
ln -s /path/to/akash-skill/skills/akash ~/.agents/skills/akash
ln -s /path/to/akash-skill/skills/akash-provider ~/.agents/skills/akash-provider
ln -s /path/to/akash-skill/skills/akash-node ~/.agents/skills/akash-node
```

### Try without installing (local clone)

Useful for Claude Code development against an unreleased branch, or for trying the plugin in a single session without persisting it:

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

In Claude Code, you can also invoke them explicitly: `/akash-network:akash`, `/akash-network:akash-provider`, `/akash-network:akash-node`. In Codex, use the same natural-language triggers; depending on the client surface, the skills may appear as `akash`, `akash-provider`, and `akash-node` under the Akash Network plugin.

## Repo layout

```
.
├── .claude-plugin/
│   ├── plugin.json              # Plugin manifest (name, version, author)
│   └── marketplace.json         # Marketplace manifest (lists this plugin)
├── .codex-plugin/
│   └── plugin.json              # Codex plugin manifest and skill path
├── .agents/
│   └── skills -> ../skills       # Agent-compatible skill discovery path
├── AGENTS.md                     # Generic coding-agent routing guidance
├── skills/
│   ├── akash/                   # Deployer skill
│   │   ├── SKILL.md
│   │   ├── agents/
│   │   │   └── openai.yaml      # Codex UI metadata
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
│   │   ├── agents/
│   │   │   └── openai.yaml      # Codex UI metadata
│   │   └── rules/
│   │       ├── requirements.md
│   │       ├── setup/           # Kubernetes, installation, config
│   │       ├── configuration/   # Attributes, pricing, bid engine
│   │       └── operations/      # Leases, monitoring, troubleshooting
│   └── akash-node/              # Node / validator skill
│       ├── SKILL.md
│       ├── agents/
│       │   └── openai.yaml      # Codex UI metadata
│       └── rules/
│           ├── overview.md
│           ├── full-node/       # Installation, requirements, state sync
│           └── validator/       # Becoming a validator, ops, security
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

The skills are written for Claude Code, Codex, OpenCode, and generic coding-agent clients, but should be readable as general Akash documentation as well.

## License

MIT — see `LICENSE`.

## Related projects

- [`akash-network/console`](https://github.com/akash-network/console) — Managed-wallet Console (UI + API)
- [`akash-network/console-air`](https://github.com/akash-network/console-air) — Self-custody Console
- [`akash-network/chain-sdk`](https://github.com/akash-network/chain-sdk) — TypeScript/Go/Rust SDKs
- [`akash-network/node`](https://github.com/akash-network/node) — Akash chain node
- [`akash-network/provider`](https://github.com/akash-network/provider) — Provider services
- [`akash-network/awesome-akash`](https://github.com/akash-network/awesome-akash) — Production-ready SDL templates
