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
cluster: nlp
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

echo "=== verify clusters.json created ==="
test -f .hippo/clusters.json && echo "clusters.json exists"
CLUSTER_COUNT=$(python3 -c "import json; print(len(json.load(open('.hippo/clusters.json'))['clusters']))")
echo "Cluster count: $CLUSTER_COUNT"

echo "=== meta --ids a (single read) ==="
hippo meta --ids a

echo "=== meta --ids a,b,c (multiple read) ==="
hippo meta --ids a,b,c

echo "=== meta --ids --sync (read with pre-sync) ==="
hippo meta --ids a --sync

echo "=== meta --ids nonexistent (error case) ==="
hippo meta --ids nonexistent 2>&1 || echo "Expected error for nonexistent topic"

echo "=== meta --set single target, single field ==="
hippo meta --ids a --set progress=completed

echo "=== meta --set multiple targets, multiple fields ==="
hippo meta --ids b,c --set cluster=nlp progress=started sources="[https://b.com,https://c.com]"

echo "=== meta --set --sync with multiple changes ==="
hippo meta --ids a --set progress=new cluster=ml aliases="[alias-a-new]" --sync

echo "=== graph (full) ==="
hippo graph | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'topics: {len(d[\"topics\"])}, clusters: {len(d[\"clusters\"])}, word_counts: {len(d[\"word_counts\"])}')"

echo "=== graph --sync (pre-sync then full) ==="
hippo graph --sync | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'topics: {len(d[\"topics\"])}')"

echo "=== graph --from a ==="
hippo graph --from a

echo "=== graph --from a --depth 1 ==="
hippo graph --from a --depth 1 | python3 -c "import json,sys; d=json.load(sys.stdin); print([t['id'] for t in d])"

echo "=== graph --from a --depth 2 ==="
hippo graph --from a --depth 2 | python3 -c "import json,sys; d=json.load(sys.stdin); print([t['id'] for t in d])"

echo "=== graph --from b --to c ==="
hippo graph --from b --to c

echo "=== graph --to c (error - requires --from) ==="
hippo graph --to c 2>&1 || echo "Expected error when --to without --from"

echo "=== clean (should report orphan, no sources, no parent, no cluster) ==="
hippo clean 2>&1 || true

echo "=== clean --sync (pre-sync then check) ==="
hippo clean --sync 2>&1 || true

echo "=== backup (creates clusters.json in backup) ==="
hippo backup

echo "=== list backups ==="
ls .hippo/backups/

BACKUP_FILE=$(ls .hippo/backups/graph_backup_*.json | head -1)
BACKUP_TS=$(basename "$BACKUP_FILE" | sed 's/graph_backup_//' | sed 's/.json//')
echo "Using backup: $BACKUP_TS"

BACKUP_CLUSTERS=$(ls .hippo/backups/clusters_backup_*.json | head -1)
echo "Backup clusters: $BACKUP_CLUSTERS"

echo "=== modify topics before restore ==="
hippo meta --ids a,b,c --set cluster=modified-cluster

echo "=== restore --version ==="
hippo restore --version "$BACKUP_TS"

echo "=== verify restore (cluster should be original values) ==="
hippo meta --ids a | grep -q "cluster: ml" && echo "Restore successful: a cluster=ml"
hippo meta --ids c | grep -q "cluster: nlp" && echo "Restore successful: c cluster=nlp"

echo "=== verify clusters.json restored ==="
test -f .hippo/clusters.json && echo "clusters.json exists after restore"
python3 -c "import json; d=json.load(open('.hippo/clusters.json')); ids=[c['id'] for c in d['clusters']]; assert 'ml' in ids and 'nlp' in ids, f'Expected ml and nlp, got {ids}'; print('clusters.json contains ml and nlp')"

echo "=== restore (most recent) ==="
hippo meta --ids a --set cluster=restored-cluster
hippo restore
hippo meta --ids a | grep -q "cluster: ml" && echo "Restore successful: a cluster=ml"

echo "=== meta --set multiple targets, reset lists ==="
hippo meta --ids b --set aliases="[new-alias]" related="[]" sources="[]"

echo "=== verify updated b ==="
hippo meta --ids b

echo "=== meta --set cluster customization survives sync ==="
echo "=== modify clusters.json manually ==="
python3 -c "
import json
d = json.load(open('.hippo/clusters.json'))
for c in d['clusters']:
    if c['id'] == 'ml':
        c['title'] = 'Machine Learning'
        c['color'] = '#FF0000'
json.dump(d, open('.hippo/clusters.json', 'w'), indent=2)
"
echo "Modified ml cluster to 'Machine Learning' / #FF0000"

echo "=== add new topic with new cluster ==="
cat > topics/d.md << 'EOF'
---
id: d
title: Topic D
aliases:
progress: new
created_at: 2026-03-19
updated_at: 2026-03-19
cluster: rl
parent:
related: []
sources: []
---
# Topic D
D content.
EOF

echo "=== sync (should merge: preserve ml customizations, add rl auto-assigned) ==="
hippo sync
python3 -c "
import json
d = json.load(open('.hippo/clusters.json'))
for c in d['clusters']:
    if c['id'] == 'ml':
        assert c['title'] == 'Machine Learning', f'Expected Machine Learning, got {c[\"title\"]}'
        assert c['color'] == '#FF0000', f'Expected #FF0000, got {c[\"color\"]}'
        print('ml customizations preserved: Machine Learning / #FF0000')
    elif c['id'] == 'rl':
        assert c['title'] == 'Rl', f'Expected Rl, got {c[\"title\"]}'
        print(f'rl auto-assigned: {c[\"title\"]} / {c[\"color\"]}')
"

echo "=== All tests passed ==="
