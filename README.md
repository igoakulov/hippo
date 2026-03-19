# Hippo

Local-first knowledge graph for agent-driven research.

## Quick Start

```bash
pip install -e .
hippo init --vault ./my-vault
cd my-vault
hippo sync
```

## Commands

```bash
hippo init --vault <path>     # Create new vault
hippo sync                    # Rebuild graph from files
hippo meta --ids <id>        # Get topic metadata
hippo meta --ids <id> --set field=value  # Update metadata
hippo graph --from <id>       # View topic neighborhood
hippo graph --from <id> --to <id2>  # Find path
hippo clean                   # Check for issues
hippo backup                  # Create backup
hippo restore                 # Restore from backup
```

## Topic Format

Topics are markdown files with YAML frontmatter:

```yaml
---
id: flashattention
title: FlashAttention
aliases: flash-attention
progress: new
created_at: 2026-03-19
updated_at: 2026-03-19
cluster: transformers
parent: attention
related: [ringattention]
sources:
  - https://arxiv.org/abs/2205.14148
---
# FlashAttention

Your notes here...
```

## Vault Structure

```
vault/
├── topics/           # Topic markdown files (source of truth)
├── chats/            # Chat exports
├── sources/          # Cached sources
└── .hippo/          # App internals
    ├── graph.json    # Derived graph
    ├── archive.json  # Source references
    ├── backups/      # Rolling backups
    └── diffs/       # Change logs
```
