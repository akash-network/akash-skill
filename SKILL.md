---
name: akash
description: >
  DEPRECATED — this standalone skill has been split into three skills and repackaged
  as the `akash-network` Claude Code plugin. Install the plugin and uninstall this
  standalone skill. See the repo README for migration instructions.
license: MIT
metadata:
  author: Akash Network
  version: "3.0.0-deprecated"
---

# Akash Skill — Deprecated (See README)

This standalone skill has been **split into three skills** and repackaged as a Claude Code plugin:

- **`akash-network:akash`** — Deploy workloads (SDL, Console API, CLI, SDKs)
- **`akash-network:akash-provider`** — Run an Akash provider
- **`akash-network:akash-node`** — Run a full node or validator

## How to migrate

1. **Remove the standalone install.** If this skill was installed by symlinking or cloning into `~/.claude/skills/akash/`, remove that directory.

2. **Install the plugin.** From the repo root (where you found this file):

   ```bash
   claude --plugin-dir /path/to/this/repo
   ```

   Or, if the plugin is published to a Claude Code marketplace your client is configured for:

   ```bash
   /plugin install akash-network
   ```

3. The three skills will then be available as `akash-network:akash`, `akash-network:akash-provider`, and `akash-network:akash-node`. The triggers in their descriptions are the same as before, just with the namespace prefix.

## Why the split?

The original skill mixed three distinct personas (deployer, provider operator, validator operator) into one description, which made it hard for Claude to pick the right skill for the right task. Splitting them sharpens trigger precision and lets each skill stay focused.

See `README.md` for the full changelog and rationale.
