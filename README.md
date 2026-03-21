# Hippo

Hippo is a tool for your AI agent to visualize, update and expand your personal knowledge locally on your device.

## Quick Start

TBD

## Commands

```bash
hippo init --vault <path>          # Create new vault
hippo sync                         # Rebuild graph from files
hippo topics                       # List topics with progress counts
hippo topics --ids <ids>          # Get metadata (single or comma-separated)
hippo topics --ids <ids> --meta field=value...   # Update metadata
hippo topics --ids <ids> --meta ... --sync       # Update then sync
hippo graph                         # View full graph
hippo graph --from <id>           # View neighborhood
hippo graph --from <id> --depth N # Traverse N levels
hippo graph --from <id> --to <id2> # Find path
hippo graph --sync                  # Sync before viewing
hippo sources                       # View source stats
hippo chatgpt --path <file>       # Ingest ChatGPT exports
hippo backup                        # Create backup
hippo restore                       # Restore (most recent)
hippo restore --version <ts>        # Restore specific backup
```

## Warnings

Add `--warnings` to any command to show and troubleshoot issues:
- `hippo sync --warnings`
- `hippo topics --warnings`
- `hippo sources --warnings`

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
├── topics/            # Topic markdown files (source of truth)
├── sources/           # Cached sources
│   └── chats/         # Chat exports
└── .hippo/            # App internals
    ├── graph.json     # Derived graph
    ├── graph.html     # Visualization
    ├── clusters.json  # Cluster colors and titles
    ├── archive.json   # Source references
    ├── backups/       # Rolling backups
    └── diffs/         # Change logs
```
