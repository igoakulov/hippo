# AGENTS.md - Hippo Development Guide

This file provides guidelines for agentic coding agents working on Hippo.

---

## Breaking Changes Policy

**No soft-deprecation.** When making breaking changes:
- Delete old code fully
- No migration scripts, no deprecated warnings

---

## Key Design Decisions

### Files as Source of Truth

Topic markdown files are primary truth. graph.json is derived display cache.

### CLI-First for Token Efficiency

Use CLI for: metadata updates (avoids full file reads), graph traversal, backup/restore.
Use files for: creating topics, editing content, searching.

### argparse over Click

For ~6 simple commands, argparse is sufficient. No extra dependency.

### Connections: Single Parent

Single `parent` field. Multiple parent needs → create intermediate topic.

---

## Code Style

- snake_case for functions/methods
- PascalCase for classes
- Built-in generics: `list[str]`, `dict[str, str]`, `str | None`
- Early returns as guards
- Annotate public functions with return types

---

## Error Handling

- Library layer: raise specific exceptions, add context when re-raising
- CLI layer: let exceptions bubble, print to stderr with non-zero exit
- Avoid broad `except Exception:`

---

## Graph Modifications

Before write operations:
1. Backup
2. Validate
3. Write diff log

---

## Testing

- pytest with unittest mocks
- Mock filesystem operations
- One assertion per test
- Descriptive names: `test_meta_get_returns_frontmatter`

---

## Important Patterns

### YAML Frontmatter
- Block between `---` delimiters
- Can appear anywhere in file
- Strip comments on parse
- Use YAML parser, not regex

### Graph Derivation
- Scan topics/*.md
- Parse frontmatter
- Build graph.json from files
- Never reverse (graph.json → files)

### Backup
- Scope: frontmatter only, not prose content
- Configurable retention (default 20)

---

## Where to Find What

- `docs/prd.md` - Full requirements
- `docs/skill.md` - Agent workflow instructions
- `docs/refactor.md` - Implementation plan
