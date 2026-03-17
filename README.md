# Hippo

Local-first knowledge graph system for agent-driven research.

## Overview

Hippo captures and organizes knowledge from X posts, ChatGPT conversations, URLs, and local documents into a structured graph. Built for agents using filesystem tools (`ls`, `rg`, `cat`, `jq`).

## Features

- **Agent-native**: Knowledge retrievable via standard CLI tools
- **Markdown nodes**: Human-readable notes with metadata
- **Graph visualization**: D3.js force-directed interactive graph
- **Safe editing**: Backup, diff, and undo system
- **Source caching**: Store X posts and ChatGPT exports locally

## Installation

```bash
pip install -e .
```

## Usage

```bash
hippo graph --cluster transformers
hippo add-node --id flashattention --title "FlashAttention"
hippo ingest-url https://arxiv.org/paper
hippo render
```

## Architecture

- CLI handles deterministic operations (storage, validation, backups)
- Agents handle reasoning, summarization, and node creation
- No databases, embeddings, or vector search required
