"""Manifest helpers for LevelUpDiag."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import detect_diag_root

MANIFEST_FILE = "levelupdiag_manifest.json"
LEVEL_ID_RE = re.compile(r"^(?:N|LUD-?)?(\d{1,2})$", re.IGNORECASE)

@dataclass(frozen=True, slots=True)
class LevelInfo:
    id: str
    name: str
    file: str
    purpose: str = ""
    requires_backend: bool = False
    requires_frontend: bool = False
    requires_playwright: bool = False
    blocking_for_release: bool = False
    category: str = ""
    raw: dict[str, Any] | None = None

    @property
    def display_title(self) -> str:
        return f"{self.id} — {self.name}"

    def file_path(self, diag_root: Path | None = None) -> Path:
        return (diag_root or detect_diag_root()) / self.file

    def requirements_label(self) -> str:
        reqs = []
        if self.requires_backend:
            reqs.append("backend")
        if self.requires_frontend:
            reqs.append("frontend")
        if self.requires_playwright:
            reqs.append("playwright")
        return ", ".join(reqs) if reqs else "aucun prérequis runtime"


def normalize_level_id(value: str) -> str:
    raw = str(value or "").strip().upper().replace(" ", "")
    m = LEVEL_ID_RE.match(raw)
    if not m:
        return raw or "N00"
    return f"N{int(m.group(1)):02d}"


def load_manifest(root: Path | None = None) -> dict[str, Any]:
    diag_root = root or detect_diag_root()
    path = diag_root / MANIFEST_FILE
    if not path.exists():
        raise FileNotFoundError(f"Missing manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def list_levels(root: Path | None = None) -> list[LevelInfo]:
    data = load_manifest(root)
    levels: list[LevelInfo] = []
    for item in data.get("levels", []):
        levels.append(LevelInfo(
            id=normalize_level_id(item.get("id", "")),
            name=str(item.get("name", "")).strip(),
            file=str(item.get("file", "")).strip(),
            purpose=str(item.get("purpose", item.get("description", ""))).strip(),
            requires_backend=bool(item.get("requires_backend", False)),
            requires_frontend=bool(item.get("requires_frontend", False)),
            requires_playwright=bool(item.get("requires_playwright", False)),
            blocking_for_release=bool(item.get("blocking_for_release", False)),
            category=str(item.get("category", "")),
            raw=item,
        ))
    return sorted(levels, key=lambda lv: lv.id)


def get_level(level_id: str, root: Path | None = None) -> LevelInfo:
    wanted = normalize_level_id(level_id)
    for level in list_levels(root):
        if level.id == wanted:
            return level
    raise KeyError(f"Unknown level: {level_id}")
