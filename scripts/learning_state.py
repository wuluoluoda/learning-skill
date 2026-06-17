#!/usr/bin/env python3
"""Manage project state for the learning skill."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


BEGIN = "<!-- BEGIN learning-managed -->"
END = "<!-- END learning-managed -->"
MANAGED_BLOCK = f"""{BEGIN}
## Learning Skill 接入

本项目启用了 learning 接入。进入本项目工作时，请读取全局 `learning` skill，并按其中规则检查项目状态。这是只读接入检查，不是显式调用，不能创建、切换或改变 learning 状态。
{END}
"""

NOTES_TEMPLATE = """# Learning Notes

## 教学偏好

- 默认使用阶段边界教学：只在自然节点简短解释关键判断。
"""

OMISSIONS_TEMPLATE = """# Learning Omissions

```json
{
  "total": 0,
  "applied": 0,
  "omissions": 0
}
```

这些条目是可能值得写入 NOTES.md、但暂时不够明确、不够稳定或不是教学偏好的候选项。它们只是审计线索，不是正式教学偏好。

## 候选项
"""


def emit(payload: dict[str, Any], code: int = 0) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(code)


def resolve_project(path: str) -> Path:
    return Path(path).expanduser().resolve()


def git_root(project: Path) -> Path | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(project), "rev-parse", "--show-toplevel"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    root = result.stdout.strip()
    return Path(root).resolve() if root else None


def learning_paths(project: Path) -> dict[str, Path]:
    learning_dir = project / ".codex" / "learning"
    return {
        "learning_dir": learning_dir,
        "state_file": learning_dir / "state.json",
        "notes_file": learning_dir / "NOTES.md",
        "omissions_file": learning_dir / "OMISSIONS.md",
        "agents_file": project / "AGENTS.md",
        "gitignore_file": project / ".gitignore",
    }


def ensure_gitignore(project: Path) -> str:
    if git_root(project) is None:
        return "not_git_repo"

    gitignore = project / ".gitignore"
    existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    lines = existing.splitlines()
    normalized = {line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")}
    covered = any(
        item in normalized
        for item in {
            ".codex/learning/",
            ".codex/learning",
            "/.codex/learning/",
            "/.codex/learning",
            ".codex/",
            ".codex",
            "/.codex/",
            "/.codex",
        }
    )
    if covered:
        return "covered"

    prefix = existing
    if prefix and not prefix.endswith("\n"):
        prefix += "\n"
    gitignore.write_text(prefix + ".codex/learning/\n", encoding="utf-8")
    return "added" if existing else "created"


def ensure_memory(project: Path) -> dict[str, str]:
    paths = learning_paths(project)
    paths["learning_dir"].mkdir(parents=True, exist_ok=True)
    gitignore_action = ensure_gitignore(project)
    notes_action = "exists"
    if not paths["notes_file"].exists():
        paths["notes_file"].write_text(NOTES_TEMPLATE, encoding="utf-8")
        notes_action = "created"
    omissions_action = "exists"
    if not paths["omissions_file"].exists():
        paths["omissions_file"].write_text(OMISSIONS_TEMPLATE, encoding="utf-8")
        omissions_action = "created"
    else:
        omissions_action = ensure_omissions_stats(paths["omissions_file"])
    return {
        "gitignore_action": gitignore_action,
        "notes_action": notes_action,
        "omissions_action": omissions_action,
    }


def ensure_omissions_stats(omissions_file: Path) -> str:
    text = omissions_file.read_text(encoding="utf-8")
    if extract_stats_block(text) is not None:
        return "exists"

    rest = text
    if rest.startswith("# Learning Omissions"):
        lines = rest.splitlines()
        heading = lines[0]
        remainder = "\n".join(lines[1:]).lstrip()
        rest = heading + "\n\n" + stats_block({"total": 0, "applied": 0, "omissions": 0}) + "\n\n" + remainder
    else:
        rest = "# Learning Omissions\n\n" + stats_block({"total": 0, "applied": 0, "omissions": 0}) + "\n\n" + rest.lstrip()
    omissions_file.write_text(rest.rstrip() + "\n", encoding="utf-8")
    return "stats_added"


def stats_block(stats: dict[str, int]) -> str:
    return "```json\n" + json.dumps(stats, ensure_ascii=False, indent=2) + "\n```"


def extract_stats_block(text: str) -> tuple[dict[str, int], int, int] | None:
    marker = "```json\n"
    start = text.find(marker)
    if start == -1:
        return None
    json_start = start + len(marker)
    end = text.find("\n```", json_start)
    if end == -1:
        return None
    try:
        raw = json.loads(text[json_start:end])
    except json.JSONDecodeError:
        return None
    if not isinstance(raw, dict):
        return None
    stats = {
        "total": int(raw.get("total", 0)),
        "applied": int(raw.get("applied", 0)),
        "omissions": int(raw.get("omissions", 0)),
    }
    return stats, start, end + len("\n```")


def bump_omissions_stats(omissions_file: Path, counter: str) -> dict[str, int]:
    ensure_omissions_stats(omissions_file)
    text = omissions_file.read_text(encoding="utf-8")
    extracted = extract_stats_block(text)
    if extracted is None:
        emit({"ok": False, "error": "invalid_omissions_stats", "omissions_file": str(omissions_file)}, 2)
    stats, start, end = extracted
    stats["total"] += 1
    stats[counter] += 1
    new_text = text[:start] + stats_block(stats) + text[end:]
    omissions_file.write_text(new_text.rstrip() + "\n", encoding="utf-8")
    return stats


def read_enabled(state_file: Path) -> int | None:
    if not state_file.exists():
        return None
    try:
        data = json.loads(state_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        emit({"ok": False, "error": "invalid_state_json", "state_file": str(state_file)}, 2)
    enabled = data.get("enabled")
    if enabled in (0, 1):
        return int(enabled)
    emit({"ok": False, "error": "invalid_enabled_value", "state_file": str(state_file)}, 2)


def write_enabled(state_file: Path, enabled: int) -> None:
    state_file.write_text(json.dumps({"enabled": enabled}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def managed_block_status(text: str) -> str:
    begin_count = text.count(BEGIN)
    end_count = text.count(END)
    if begin_count == 0 and end_count == 0:
        return "missing"
    if begin_count == 1 and end_count == 1 and text.index(BEGIN) < text.index(END):
        return "complete"
    return "corrupt"


def upsert_agents_block(agents_file: Path) -> str:
    text = agents_file.read_text(encoding="utf-8") if agents_file.exists() else ""
    status = managed_block_status(text)
    if status == "corrupt":
        emit({"ok": False, "error": "managed_block_corrupt", "agents_file": str(agents_file)}, 2)

    if status == "complete":
        start = text.index(BEGIN)
        end = text.index(END) + len(END)
        new_text = text[:start].rstrip() + "\n\n" + MANAGED_BLOCK + text[end:].lstrip()
        action = "replaced"
    else:
        prefix = text.rstrip()
        new_text = (prefix + "\n\n" if prefix else "") + MANAGED_BLOCK
        action = "added" if text else "created"

    agents_file.write_text(new_text.rstrip() + "\n", encoding="utf-8")
    return action


def remove_agents_block(agents_file: Path) -> str:
    if not agents_file.exists():
        return "missing"
    text = agents_file.read_text(encoding="utf-8")
    status = managed_block_status(text)
    if status == "missing":
        return "missing"
    if status == "corrupt":
        emit({"ok": False, "error": "managed_block_corrupt", "agents_file": str(agents_file)}, 2)

    start = text.index(BEGIN)
    end = text.index(END) + len(END)
    new_text = (text[:start] + text[end:]).strip()
    if not new_text:
        agents_file.unlink()
        return "deleted_file"
    agents_file.write_text(new_text.rstrip() + "\n", encoding="utf-8")
    return "removed"


def check_agents_block(agents_file: Path) -> None:
    if not agents_file.exists():
        return
    status = managed_block_status(agents_file.read_text(encoding="utf-8"))
    if status == "corrupt":
        emit({"ok": False, "error": "managed_block_corrupt", "agents_file": str(agents_file)}, 2)


def base_payload(project: Path) -> dict[str, Any]:
    paths = learning_paths(project)
    return {
        "project_dir": str(project),
        "learning_dir": str(paths["learning_dir"]),
        "state_file": str(paths["state_file"]),
        "notes_file": str(paths["notes_file"]),
        "omissions_file": str(paths["omissions_file"]),
        "agents_file": str(paths["agents_file"]),
    }


def cmd_status(project: Path) -> None:
    paths = learning_paths(project)
    enabled = read_enabled(paths["state_file"])
    payload = base_payload(project)
    payload.update({"ok": True, "enabled": enabled, "state": "missing" if enabled is None else ("enabled" if enabled else "disabled")})
    emit(payload)


def cmd_ensure(project: Path) -> None:
    actions = ensure_memory(project)
    payload = base_payload(project)
    payload.update({"ok": True, **actions})
    emit(payload)


def cmd_bump(project: Path, counter: str | None) -> None:
    if counter not in {"applied", "omissions"}:
        emit({"ok": False, "error": "invalid_counter", "counter": counter}, 2)
    actions = ensure_memory(project)
    paths = learning_paths(project)
    stats = bump_omissions_stats(paths["omissions_file"], counter)
    payload = base_payload(project)
    payload.update({"ok": True, "counter": counter, "stats": stats, **actions})
    emit(payload)


def cmd_toggle(project: Path) -> None:
    paths = learning_paths(project)
    current = read_enabled(paths["state_file"])
    enabled = 1 if current is None else 0 if current == 1 else 1
    check_agents_block(paths["agents_file"])
    actions = ensure_memory(project)
    agents_action = upsert_agents_block(paths["agents_file"]) if enabled else remove_agents_block(paths["agents_file"])
    write_enabled(paths["state_file"], enabled)
    payload = base_payload(project)
    payload.update(
        {
            "ok": True,
            "previous_enabled": current,
            "enabled": enabled,
            "state": "enabled" if enabled else "disabled",
            "agents_action": agents_action,
            **actions,
        }
    )
    emit(payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage learning skill project state.")
    parser.add_argument("action", choices=["toggle", "ensure", "status", "bump"])
    parser.add_argument("--project", default=".", help="Project directory. Defaults to the current directory.")
    parser.add_argument("--counter", choices=["applied", "omissions"], help="Counter to increment for bump.")
    args = parser.parse_args()

    project = resolve_project(args.project)
    if args.action == "toggle":
        cmd_toggle(project)
    if args.action == "ensure":
        cmd_ensure(project)
    if args.action == "status":
        cmd_status(project)
    if args.action == "bump":
        cmd_bump(project, args.counter)


if __name__ == "__main__":
    main()
