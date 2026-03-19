from pathlib import Path

CONFIG_DIR = Path.home() / ".hippo"
CONFIG_FILE = CONFIG_DIR / "config"
DEFAULT_VAULT_DIR = Path.cwd()


def ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict[str, str]:
    ensure_config_dir()
    if not CONFIG_FILE.exists():
        return {}
    config = {}
    for line in CONFIG_FILE.read_text().splitlines():
        line = line.strip()
        if "=" in line:
            key, value = line.split("=", 1)
            config[key.strip()] = value.strip()
    return config


def save_config(config: dict[str, str]) -> None:
    ensure_config_dir()
    lines = [f"{k}={v}" for k, v in config.items()]
    CONFIG_FILE.write_text("\n".join(lines) + "\n")


def get_vault_dir() -> Path | None:
    config = load_config()
    if "vault_dir" in config:
        return Path(config["vault_dir"])
    return None


def set_vault_dir(vault_dir: Path) -> None:
    config = load_config()
    config["vault_dir"] = str(vault_dir)
    save_config(config)


def init_vault(vault_path: Path) -> None:
    vault_path = vault_path.resolve()
    if vault_path.exists() and any(vault_path.iterdir()):
        raise ValueError(f"Directory {vault_path} is not empty")

    vault_path.mkdir(parents=True, exist_ok=True)
    (vault_path / "topics").mkdir(parents=True, exist_ok=True)
    (vault_path / "chats").mkdir(parents=True, exist_ok=True)
    (vault_path / "sources").mkdir(parents=True, exist_ok=True)
    (vault_path / "sources/x_posts").mkdir(parents=True, exist_ok=True)
    (vault_path / ".hippo").mkdir(parents=True, exist_ok=True)
    (vault_path / ".hippo/backups").mkdir(parents=True, exist_ok=True)
    (vault_path / ".hippo/diffs").mkdir(parents=True, exist_ok=True)

    agents_content = """---
id: AGENTS
title: Hippo Agent Skill
aliases: hippo,claude
progress: new
created_at: 2026-03-19
updated_at: 2026-03-19
cluster:
parent:
related: []
sources:
---
# Hippo Agent Skill

See [skill.md](docs/skill.md) for full instructions.

## Topic Format

Topics are markdown files with YAML frontmatter:

\\`\\`\\`yaml
---
id: topic-id
title: Topic Title
aliases: alias1,alias2
progress: new|started|completed
created_at: YYYY-MM-DD
updated_at: YYYY-MM-DD
cluster: cluster-id
parent: parent-topic-id
related: [related1, related2]
sources:
  - https://example.com/source
  - ~/documents/file.pdf
---
# Topic Title

Your notes here...
\\`\\`\\`

## Quick Commands

- List topics: `ls topics/`
- Get metadata: `hippo meta --ids <id>`
- Set metadata: `hippo meta --ids <id> --set field=value`
- Search: `grep "keyword" topics/*.md`
- Graph: `hippo graph --from <id> --depth N`
"""
    (vault_path / "topics/AGENTS.md").write_text(agents_content)
    set_vault_dir(vault_path)
