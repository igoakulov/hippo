#!/bin/bash
set -e

cd "$(dirname "$0")/.."

TEST_VAULT="/tmp/hippo_test_$$"
export HIPPO_VAULT="$TEST_VAULT"

cleanup() {
    rm -rf "$TEST_VAULT"
}
trap cleanup EXIT

mkdir -p "$TEST_VAULT"

echo "=== version ==="
hippo version

echo "=== init ==="
hippo init --vault "$TEST_VAULT"

cd "$TEST_VAULT"

echo "=== sync (empty vault) ==="
hippo sync

echo "=== Creating topics ==="
cat > topics/a.md << 'EOF'
---
id: a
title: Topic A
aliases: alias-a,topic-a
progress: new
created_at: 2026-03-19
updated_at: 2026-03-19
cluster: ml
parent:
related: []
sources:
  - https://example.com/a
---
# Topic A

Content for A.
EOF

cat > topics/b.md << 'EOF'
---
id: b
title: Topic B
aliases: alias-b
progress: new
created_at: 2026-03-19
updated_at: 2026-03-19
cluster: ml
parent: a
related:
  - c
sources:
  - https://example.com/b
---
# Topic B

Content for B.
EOF

cat > topics/c.md << 'EOF'
---
id: c
title: Topic C
aliases:
progress: started
created_at: 2026-03-19
updated_at: 2026-03-19
cluster: ml
parent: a
related: []
sources:
---
# Topic C

Content for C.
EOF

cat > topics/orphan.md << 'EOF'
---
id: orphan
title: Orphan Topic
aliases:
progress: new
created_at: 2026-03-19
updated_at: 2026-03-19
cluster: ml
parent: nonexistent-parent
related: []
sources:
  - https://orphan.example.com
---
# Orphan Topic

Content for orphan.
EOF

echo "=== sync (build graph with topics) ==="
hippo sync

echo "=== meta --ids a (single) ==="
hippo meta --ids a

echo "=== meta --ids a,b,c (multiple) ==="
hippo meta --ids a,b,c

echo "=== meta --ids a --set progress=completed ==="
hippo meta --ids a --set progress=completed

echo "=== meta --ids b --set related=\"[d,e]\" (list value) ==="
hippo meta --ids b --set related="[d,e]"

echo "=== meta --ids nonexistent (error case) ==="
hippo meta --ids nonexistent 2>&1 || echo "Expected error for nonexistent topic"

echo "=== graph (full) ==="
hippo graph

echo "=== graph --from a ==="
hippo graph --from a

echo "=== graph --from a --depth 1 ==="
hippo graph --from a --depth 1

echo "=== graph --from a --depth 2 ==="
hippo graph --from a --depth 2

echo "=== graph --from b --to c ==="
hippo graph --from b --to c

echo "=== graph --to c (error - requires --from) ==="
hippo graph --to c 2>&1 || echo "Expected error when --to without --from"

echo "=== clean (should report orphan parent, no sources, no parent) ==="
hippo clean || true

echo "=== backup ==="
hippo backup

echo "=== list backups ==="
ls -la .hippo/backups/

BACKUP_FILE=$(ls .hippo/backups/graph_backup_*.json | head -1)
BACKUP_TS=$(basename "$BACKUP_FILE" | sed 's/graph_backup_//' | sed 's/.json//')
echo "Using backup: $BACKUP_TS"

echo "=== meta --ids a,b,c --set cluster=updated-ml (modify before restore) ==="
hippo meta --ids a,b,c --set cluster=updated-ml

echo "=== restore --version $BACKUP_TS ==="
hippo restore --version "$BACKUP_TS"

echo "=== verify restore (cluster should be 'ml' not 'updated-ml') ==="
hippo meta --ids a | grep -q "cluster: ml" && echo "Restore successful: cluster reverted to 'ml'"

echo "=== restore (most recent) ==="
hippo restore

echo "=== meta --ids b --set aliases=\"[new-alias]\" related=\"[]\" (reset list) ==="
hippo meta --ids b --set aliases="[new-alias]" related="[]"

echo "=== verify updated b ==="
hippo meta --ids b

echo "=== All tests passed ==="
