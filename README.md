# Hippo

Local-first knowledge graph system for agent-driven research.

## Overview

Hippo captures and organizes your personal interests and knowledge from X activity, ChatGPT conversations, URLs, and local documents into a structured graph. Your agent handles everything from maintenance to proactive suggestions. Built for agents using filesystem tools (`ls`, `rg`, `cat`, `jq`).

## Installation and Setup

- Install agent skill
- Optionally set up X API key or provide ChatGPT export to your agent
- Agent does the rest

## Features

- **Agent-native**: Knowledge retrievable via standard CLI tools
- **Markdown nodes**: Human-readable notes with metadata
- **Graph visualization**: D3.js force-directed interactive graph
- **Safe editing**: Backup, diff, and undo system
- **Source caching**: Store X posts and ChatGPT exports locally

## Architecture

- CLI handles deterministic operations (storage, validation, backups)
- Agents handle reasoning, summarization, and node creation
- All data is stored locally
- No databases, embeddings, or vector search required
