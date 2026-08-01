# Guidance for Coding Agents

This repository packages Akash Network skills for multiple coding-agent clients. The canonical skill content lives under `skills/`.

## Skill Routing

- For Akash workload deployment, SDL, Console API, CLI, SDK, authz, bid matching, or AkashML tasks, read `skills/akash/SKILL.md`.
- For Akash provider setup, Kubernetes provider operations, attributes, pricing, bid engine, monitoring, or troubleshooting, read `skills/akash-provider/SKILL.md`.
- For Akash full node, validator, state sync, validator security, slashing, or sentry-node tasks, read `skills/akash-node/SKILL.md`.

Resolve relative rule links from the skill directory that contains the `SKILL.md` file.

## Platform Paths

- Claude Code uses `.claude-plugin/`.
- Codex uses `.codex-plugin/plugin.json` and the optional `agents/openai.yaml` files under each skill.
- OpenCode and generic agent-compatible clients can discover the same skills through `.agents/skills`, which points to the canonical `skills/` directory.
