# Hippo

Hippo is a local-first knowledge graph for agent-driven research.

## Overview

Hippo captures and organizes knowledge from X posts, ChatGPT conversations, URLs, and local documents into a structured graph. Built for agents using filesystem tools (`ls`, `rg`, `cat`, `jq`).

## Installation

Install agent skill, agent will set up the rest.

## Commands

```bash
# Topics (nodes)
hippo topic add --ids a,b,c --cluster transformers
hippo topic update --ids a --progress started
hippo topic delete --ids a,b
hippo topic list

# Connections
hippo conn add a b --type parent
hippo conn add a b,c --type parent  # bulk targets
hippo conn remove a b
hippo conn list a

# Graph queries
hippo graph --cluster transformers
hippo graph --from flashattention --depth 2
hippo graph --path a b

# System
hippo sync        # sync metadata, re-create missing files
hippo render      # generate visualization (future)
hippo backup      # backup graph (future)
```

## File Structure

```
graph.json         # clusters + topics (single source of truth)
topics/           # topic markdown files
  a.md
  b.md
sources/          # cached sources
backups/          # backups
diffs/            # change history
render/           # visualization output
```

## Topic Markdown Format (9 lines)

```
id: flashattention
title: FlashAttention
aliases: flash-attention, flash attention
progress: new
cluster: transformers
created: 2026-03-15
updated: 2026-03-20
sources: https://x.com/user/123
connections: parent:attention;related:ringattention

# FlashAttention

[content]
```

## Agent Discovery

```bash
# List all titles
grep "^title:" topics/*.md

# Find by keyword
grep "attention" topics/*.md

# Get metadata (first 9 lines)
head topics/flashattention.md
```
