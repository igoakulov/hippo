#!/bin/bash
set -e

cd "$(dirname "$0")/.."

# Setup - clean first
rm -f graph.json topics/*.md

# Create topics
uv run hippo topic add --ids a,b,c --cluster transformers
uv run hippo topic add --ids d

# Update
uv run hippo topic update --ids a --progress started

# List
echo "=== topic list ==="
uv run hippo topic list
echo "=== topic list --cluster transformers ==="
uv run hippo topic list --cluster transformers

# Connections
uv run hippo conn add a b,c --type parent
uv run hippo conn add a d --type related
echo "=== conn list a ==="
uv run hippo conn list a

# Graph queries
echo "=== graph --cluster transformers ==="
uv run hippo graph --cluster transformers
echo "=== graph --from a --depth 1 ==="
uv run hippo graph --from a --depth 1
echo "=== graph --from a --path d ==="
uv run hippo graph --from a --path d

# Sync re-creation
rm topics/a.md
echo "=== sync (re-create) ==="
uv run hippo sync
test -f topics/a.md || { echo "FAILED: a.md not recreated"; exit 1; }

# Cleanup
uv run hippo topic delete --ids a,b,c,d
rm -f graph.json topics/*.md

echo "=== All tests passed ==="
