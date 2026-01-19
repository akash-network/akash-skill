# Akash SDL Skill for Claude Code

A Claude Code skill that generates valid Akash Network SDL (Stack Definition Language) configurations for deploying containerized applications on the decentralized cloud.

## Installation

```bash
claude skill add https://github.com/akash-network/akash-sdl-skill
```

## Usage

Once installed, Claude will automatically use this skill when you ask it to:

- "Create an Akash deployment for..."
- "Generate SDL for..."
- "Deploy to Akash..."
- "Create Akash config for..."

### Examples

```
> Generate an SDL for a simple nginx web server

> Create an Akash deployment for WordPress with a MySQL database

> Deploy a GPU workload with an NVIDIA A100 on Akash

> Generate SDL for a game server with a dedicated IP
```

## What's Included

### Rules
- **schema-overview.md** - SDL structure and version requirements
- **services.md** - Service configuration (image, expose, env, credentials)
- **compute-resources.md** - CPU, memory, storage, and GPU specifications
- **placement-pricing.md** - Provider selection and pricing (uakt/USDC)
- **deployment.md** - Service-to-profile mapping
- **endpoints.md** - IP endpoint configuration (v2.1)
- **validation-rules.md** - All constraints and validation rules

### Examples
- **web-app.md** - Simple web deployment
- **wordpress-db.md** - Multi-service with persistent storage
- **gpu-workload.md** - GPU deployment with NVIDIA
- **ip-lease.md** - IP endpoint configuration

## Features

- **SDL v2.0 and v2.1** support (IP endpoints)
- **All resource types**: CPU, memory, storage classes, GPUs
- **Payment options**: uakt (native AKT) and USDC via IBC
- **Persistent storage** with beta2/beta3/ram classes
- **GPU models**: A100, T4, RTX 3090, and more
- **IP lease endpoints** for custom domains
- **Comprehensive validation** rules

## Resources

- [awesome-akash](https://github.com/akash-network/awesome-akash) - 100+ production-ready SDL templates
- [Akash Network Docs](https://akash.network/docs/)
- [chain-sdk](https://github.com/akash-network/chain-sdk) - Official SDL schema reference

## License

MIT
