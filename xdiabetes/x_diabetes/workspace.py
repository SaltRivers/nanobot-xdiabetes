"""Workspace bootstrap helpers for the X-Diabetes profile."""

from __future__ import annotations

from importlib.resources import files as pkg_files
from pathlib import Path

from xdiabetes.x_diabetes.constants import (
    DIRECTORY_TEMPLATES,
    LEARNING_DIRECTORY_TEMPLATES,
    ROOT_TEMPLATE_FILES,
)


def prepare_xdiabetes_workspace(workspace: Path, mode: str, silent: bool = False) -> list[str]:
    """Create an isolated X-Diabetes workspace with seeded assets.

    The helper copies packaged templates into the target workspace. Files are
    created only when missing, except ``USER.md`` which is refreshed on each run
    because it embeds the current operating mode (doctor or patient).
    """

    template_root = pkg_files("xdiabetes") / "templates" / "x_diabetes"
    if not template_root.is_dir():
        return []

    workspace.mkdir(parents=True, exist_ok=True)
    created: list[str] = []

    for dirname in DIRECTORY_TEMPLATES:
        target_dir = workspace / dirname
        if not target_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)
            created.append(str(target_dir.relative_to(workspace)))

    for filename in ROOT_TEMPLATE_FILES:
        source = template_root / filename
        target = workspace / filename
        content = source.read_text(encoding="utf-8")
        if filename == "USER.md":
            rendered = content.replace("{{MODE}}", mode)
            if not target.exists() or target.read_text(encoding="utf-8") != rendered:
                target.write_text(rendered, encoding="utf-8")
                if filename not in created:
                    created.append(filename)
            continue
        if not target.exists():
            target.write_text(content, encoding="utf-8")
            created.append(filename)

    for directory in ("cases", "knowledge", "playbooks", "rules", "reports"):
        source_dir = template_root / directory
        target_dir = workspace / directory
        for item in source_dir.iterdir():
            target = target_dir / item.name
            if not target.exists():
                target.write_text(item.read_text(encoding="utf-8"), encoding="utf-8")
                created.append(str(target.relative_to(workspace)))

    learning_root = workspace / "learning"
    for dirname in LEARNING_DIRECTORY_TEMPLATES:
        target_dir = learning_root / dirname
        if not target_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)
            created.append(str(target_dir.relative_to(workspace)))

    template_learning_dir = template_root / "learning"
    if template_learning_dir.is_dir():
        for item in template_learning_dir.rglob("*"):
            if not item.is_file():
                continue
            relative = item.relative_to(template_learning_dir)
            target = learning_root / relative
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(item.read_text(encoding="utf-8"), encoding="utf-8")
                created.append(str(target.relative_to(workspace)))

    memory_dir = workspace / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    for filename, default_content in {"MEMORY.md": "", "HISTORY.md": ""}.items():
        target = memory_dir / filename
        if not target.exists():
            target.write_text(default_content, encoding="utf-8")
            created.append(str(target.relative_to(workspace)))

    if created and not silent:
        from rich.console import Console

        console = Console()
        for path in created:
            console.print(f"  [dim]Created {path}[/dim]")

    return created
