"""Obsidian vault connector used by the DGM-MAT public connector boundary."""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("dgm_mat_connectors.obsidian")


class ObsidianConnector:
    """Index and write DGM-MAT operational notes in an Obsidian vault."""

    def __init__(self, vault_path: str | os.PathLike[str] | None = None) -> None:
        configured = vault_path or os.environ.get("DGM_OBSIDIAN_VAULT")
        if configured:
            self.vault_path = Path(configured)
        else:
            base = os.environ.get("DGM_BASE_PATH")
            self.vault_path = (
                Path(base) / "storage" / "obsidian-vault"
                if base
                else Path("storage") / "obsidian-vault"
            )
        self._ensure_structure()
        self.indexed_notes: list[dict[str, Any]] = []

    def _ensure_structure(self) -> None:
        for subdir in ("missions", "architecture", "memory", "evolution", "context", "repos"):
            try:
                (self.vault_path / subdir).mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                logger.warning("Could not create Obsidian vault structure: %s", exc)
                return

    def index_vault(self) -> dict[str, Any]:
        """Index Markdown notes and discover Obsidian wiki-links."""
        if not self.vault_path.exists():
            return {"status": "error", "message": "Vault not found"}

        self.indexed_notes = []
        try:
            for note in self.vault_path.rglob("*.md"):
                try:
                    content = note.read_text(encoding="utf-8")
                    self.indexed_notes.append({
                        "name": note.stem,
                        "path": str(note.relative_to(self.vault_path)),
                        "size": len(content),
                        "tags": sorted(set(re.findall(r"#[a-zA-Z0-9_\-/]+", content))),
                        "links": self._extract_links(content),
                        "mtime": os.path.getmtime(note),
                        "snippet": content[:200],
                    })
                except (OSError, UnicodeError):
                    continue
        except (PermissionError, OSError):
            logger.error("Permission denied while indexing Obsidian vault.")

        return {
            "vault": str(self.vault_path),
            "total_notes": len(self.indexed_notes),
            "notes": self.indexed_notes,
        }

    @staticmethod
    def _extract_links(content: str) -> list[str]:
        return re.findall(r"\[\[(.*?)\]\]", content)

    def create_mission_note(self, mission_data: dict[str, Any]) -> bool:
        mission_id = mission_data.get("id", "unknown")
        title = mission_data.get("title", f"Mission {mission_id}")
        content = (
            f"# {title}\n\n"
            f"**ID:** {mission_id}\n"
            f"**Status:** {mission_data.get('status', 'unknown')}\n"
            f"**Timestamp:** {datetime.now().isoformat()}\n\n"
            "## Objective\n"
            f"{mission_data.get('objective', 'No objective specified.')}\n\n"
        )
        related = mission_data.get("related_notes", [])
        if related:
            content += "## Related Notes\n"
            content += "".join(f"- [[{note}]]\n" for note in related)
        return self.export_to_markdown("missions", f"mission_{mission_id}", content)

    def sync_repo_to_vault(self, repo_stats: dict[str, Any]) -> bool:
        repo_name = repo_stats.get("name")
        if not repo_name:
            return False
        content = (
            f"# Repo: {repo_name}\n\n"
            f"**Path:** {repo_stats.get('path')}\n"
            f"**Stacks:** {', '.join(repo_stats.get('stacks', []))}\n"
            f"**Debt Score:** {repo_stats.get('debt_score', 0.0)}\n\n"
            "## Description\n"
            "Automatically indexed from DGM-MAT Cognitive Filesystem.\n\n"
        )
        return self.export_to_markdown("repos", f"repo_{repo_name}", content)

    def export_to_markdown(self, category: str, filename: str, content: str) -> bool:
        target_dir = self.vault_path / category
        target_dir.mkdir(parents=True, exist_ok=True)
        if not filename.endswith(".md"):
            filename += ".md"
        try:
            (target_dir / filename).write_text(content, encoding="utf-8")
            return True
        except OSError as exc:
            logger.error("Obsidian export failed: %s", exc)
            return False


obsidian_connector = ObsidianConnector()
