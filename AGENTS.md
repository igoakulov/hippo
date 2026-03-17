# AGENTS.md - Hippo Development Guide

This file provides guidelines for agentic coding agents working on Hippo.

---

## 1. Build / Lint / Test Commands

```bash
# Development setup
uv sync
uv sync --all-extras    # with dev dependencies

# Using Makefile
make test              # Run CLI tests
make clean             # Remove generated files and cache
make lint              # Run linter
make format            # Format code

# Manual commands
uv run ruff check src/
uv run ruff format src/

# CLI help
uv run hippo --help
uv run hippo graph --help
```

---

## 2. Project Structure

```
hippo/
├── src/hippo/
│   ├── __init__.py
│   ├── cli.py              # Click CLI commands
│   ├── models.py           # Node, Cluster, Edge, Source
│   ├── storage.py          # JSON graph storage
│   ├── validation.py       # graph validation
│   ├── graph_ops.py        # graph operations (add/remove nodes, edges)
│   ├── ingestion/          # source handlers
│   │   ├── __init__.py
│   │   ├── url.py
│   │   ├── file.py
│   │   ├── x_posts.py
│   │   └── chatgpt.py
│   └── visualization/      # D3.js templates
│       ├── __init__.py
│       └── template.html
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_storage.py
│   └── test_graph_ops.py
├── pyproject.toml
└── uv.lock
```

---

## 3. Code Style Guidelines

### 3.1 Python Conventions

- **Functions/methods**: snake_case (e.g., `add_node`, `get_cluster`)
- **Classes**: PascalCase (e.g., `Node`, `GraphStore`)
- **Constants**: ALL_CAPS (e.g., `DEFAULT_CLUSTER`)
- **Files/modules**: snake_case (e.g., `graph_ops.py`, `storage.py`)

### 3.2 Imports

```python
# Standard library
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

# Third-party
import click

# Local
from hippo.models import Node, Cluster
from hippo.storage import GraphStore
```

Group in order: stdlib → third-party → local. Alphabetize within groups.

### 3.3 Type Annotations

Use built-in generics (PEP 585):
- `list[str]` not `List[str]`
- `dict[str, str]` not `Dict[str, str]`
- `str | None` not `Optional[str]`

```python
def get_nodes(cluster: str | None = None) -> list[Node]:
    ...

def node_exists(node_id: str) -> bool:
    ...
```

### 3.4 Function Design

- Use descriptive parameter names
- Keep arity small; use dataclasses for many parameters
- Prefer single return at end; use early returns as guards
- Annotate all public functions with return types

### 3.5 Class Structure

```python
class GraphStore:
    # ======================
    # Static Fields
    # ======================
    DEFAULT_PATH = "graphs/graph.json"

    # ======================
    # Instance Fields
    # ======================
    def __init__(self, path: str):
        self._path = Path(path)
        self._data: dict | None = None

    # ======================
    # Properties
    # ======================
    @property
    def nodes(self) -> list[Node]:
        ...

    # ======================
    # Methods
    # ======================
    def load(self) -> None:
        ...

    def save(self) -> None:
        ...
```

---

## 4. Data Models

### 4.1 Node

```json
{
  "id": "flashattention",
  "title": "FlashAttention",
  "aliases": ["flash attention", "flash-attention"],
  "tags": "transformer attention,efficient attention,gpu kernel",
  "status": "new|started|completed",
  "cluster": "transformers",
  "activity_score": 0.7,
  "created_at": "2026-03-15T10:00:00Z",
  "updated_at": "2026-03-20T15:30:00Z",
  "sources": [
    {"type": "x_post", "id": "178223234"},
    {"type": "conversation", "file": "conversation_abc.md"},
    {"type": "local_file", "path": "~/papers/flashattention.pdf"},
    {"type": "url", "url": "https://arxiv.org/..."}
  ]
}
```

### 4.2 Cluster

```json
{
  "id": "transformers",
  "title": "Transformers",
  "node_ids": ["flashattention", "kv_cache", "diffusion"]
}
```

### 4.3 Edge

```json
{
  "source": "attention",
  "target": "flashattention",
  "type": "depth | semantic | reference"
}
```

---

## 5. Error Handling

### 5.1 CLI Layer (user-facing)

- Let exceptions bubble up - don't catch just to log
- CLI boundary catches and prints errors to stderr with non-zero exit code
- Provide helpful hints when applicable

```python
@click.command()
def add_node(...):
    store.add_node(node)
```

### 5.2 Library Layer

- Raise specific exceptions (ValueError, RuntimeError, FileNotFoundError)
- Add context when re-raising
- Avoid broad `except Exception:`

```python
def load_graph(self, path: Path) -> Graph:
    if not path.exists():
        raise FileNotFoundError(f"Graph file not found: {path}")
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {path}: {e}") from e
```

---

## 6. Graph Operations

All graph modifications MUST:
1. Create backup before changes
2. Run validation after changes
3. Write diff log

Commands:
- `hippo add-node`, `hippo update-node`, `hippo delete-node`
- `hippo add-edge`, `hippo remove-edge`
- `hippo merge-nodes`, `hippo clean-tags`

---

## 7. Source Ingestion

| Source Type | Storage | Command |
|-------------|---------|---------|
| URL | Reference only | `hippo ingest-url` |
| Local file | Reference only | `hippo ingest-file` |
| X post | JSON in `sources/x_posts/` | `hippo ingest-x` |
| ChatGPT | Markdown in `sources/conversations/` | `hippo ingest-chatgpt` |

---

## 8. Testing Guidelines

- Use `pytest` with standard library `unittest` mocks
- Mock external services and filesystem operations
- Test one thing per test function
- Use descriptive test names: `test_add_node_creates_backup`

---

## 9. Visualization

- D3.js force-directed graph in `src/hippo/visualization/`
- Output to `render/graph.html`
- Nodes colored by cluster, ring for completion status, glow for activity
- Support zoom, pan, hover, click interactions
- Filters: tags, status, cluster, activity, creation date
