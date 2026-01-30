# Akash Network Skill for Claude Code

A comprehensive Claude Code skill for working with the Akash Network - the decentralized cloud computing marketplace. Covers SDL generation, deployments, provider operations, node management, and SDK integration.

## Installation

using [skills-cli](https://github.com/vercel-labs/skills):

```bash
npx skills add akash-network/akash-skill
```

## Usage

Once installed, Claude will automatically use this skill when you ask it to:

**SDL & Deployments:**

- "Create an Akash deployment for..."
- "Generate SDL for..."
- "Deploy to Akash..."

**CLI & API:**

- "How do I deploy with Akash CLI?"
- "Use the Console API to deploy..."
- "Show me Akash CLI commands..."

**SDKs:**

- "Deploy using the Akash TypeScript SDK..."
- "Integrate Akash in my Node.js app..."

**Providers & Nodes:**

- "How do I become an Akash provider?"
- "Set up an Akash validator..."
- "Run an Akash full node..."

### Examples

```
> Generate an SDL for a simple nginx web server

> Create an Akash deployment for WordPress with a MySQL database

> Deploy a GPU workload with an NVIDIA A100 on Akash

> Generate SDL for a game server with a dedicated IP

> How do I deploy using the Console API?

> Show me how to use the TypeScript SDK to create a deployment

> What are the requirements to become an Akash provider?
```

## Usage by Agent

This skill can be used with various AI coding assistants:

### Claude Code

```bash
# for device-global claude configuration
git clone https://github.com/akash-network/akash-skill.git ~/.claude/skills/akash
# for project specific claude configuration (in your project workspace)
git clone https://github.com/akash-network/akash-skill.git .claude/skills/akash
```

### Cursor

Copy the contents of the `rules/` directory to your project's `.cursorrules` file or add as project rules in Cursor settings.

### Windsurf

Add the rules content to Cascade rules or memory for persistent context.

### Cline

Add as custom instructions in Cline extension settings.

### Codex / OpenCode

Include the rules as system prompt context when initializing your session.

### Generic Integration

For other AI assistants or custom setups, reference the [`rules/`](./rules/) directory directly. Each markdown file contains structured guidelines that can be adapted to any LLM's instruction format.

## What's Included

### Core Concepts

- **overview.md** - Akash Network introduction and architecture
- **terminology.md** - Key terms (lease, bid, dseq, gseq, oseq)
- **pricing.md** - Payment with uakt, USDC, IBC denoms

### SDL Configuration (`rules/sdl/`)

- **schema-overview.md** - SDL structure and version requirements
- **services.md** - Service configuration (image, expose, env, credentials)
- **compute-resources.md** - CPU, memory, storage, and GPU specifications
- **placement-pricing.md** - Provider selection and pricing (uakt/USDC)
- **deployment.md** - Service-to-profile mapping
- **endpoints.md** - IP endpoint configuration (v2.1)
- **validation-rules.md** - All constraints and validation rules

### SDL Examples (`rules/sdl/examples/`)

- **web-app.md** - Simple web deployment
- **wordpress-db.md** - Multi-service with persistent storage
- **gpu-workload.md** - GPU deployment with NVIDIA
- **ip-lease.md** - IP endpoint configuration

### Deployment Methods (`rules/deploy/`)

- **overview.md** - Comparison of deployment options
- **cli/** - Akash CLI installation, wallet setup, deployment lifecycle
- **console-api/** - Console API authentication, managed wallets, endpoints
- **certificates/** - JWT and mTLS authentication

### SDK Documentation (`rules/sdk/`)

- **overview.md** - SDK comparison and selection
- **typescript/** - TypeScript SDK for web and Node.js
- **go/** - Go SDK for backend services

### AuthZ (`rules/authz/`)

- Fee grants and deployment authorization

### Provider Operations (`rules/provider/`)

- **overview.md** - Provider requirements
- **setup/** - Kubernetes cluster and provider installation
- **configuration/** - Attributes, pricing, bid engine
- **operations/** - Monitoring and troubleshooting

### Node Operations (`rules/node/`)

- **overview.md** - Running Akash nodes
- **full-node/** - Full node setup and state sync
- **validator/** - Validator operations and security

### Reference (`rules/reference/`)

- **storage-classes.md** - beta2, beta3, ram storage
- **gpu-models.md** - Supported NVIDIA GPUs
- **ibc-denoms.md** - Payment denominations
- **rpc-endpoints.md** - Public RPC endpoints

## Features

- **SDL v2.0 and v2.1** support (IP endpoints)
- **All resource types**: CPU, memory, storage classes, GPUs
- **Payment options**: uakt (native AKT) and USDC via IBC
- **Persistent storage** with beta2/beta3/ram classes
- **GPU models**: A100, T4, RTX 3090, and more
- **IP lease endpoints** for custom domains
- **Comprehensive validation** rules
- **Console API** integration for programmatic deployments
- **TypeScript & Go SDKs** for application integration
- **Provider setup** documentation
- **Validator & node** operation guides

## Resources

- [awesome-akash](https://github.com/akash-network/awesome-akash) - 100+ production-ready SDL templates
- [Akash Network Docs](https://akash.network/docs/) - Official documentation
- [Console](https://console.akash.network) - Web-based deployment interface
- [Console API](https://console-api.akash.network/v1/swagger) - REST API documentation
- [chain-sdk](https://github.com/akash-network/chain-sdk) - Official TypeScript SDK
- [skills-cli](https://skills.sh/) - Vercel Skills CLI tooling 

## License

MIT
