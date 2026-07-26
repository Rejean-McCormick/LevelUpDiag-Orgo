"""Artifact path helpers."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def safe_slug(value: str) -> str:
    cleaned = []
    for ch in value.strip().lower():
        if ch.isalnum():
            cleaned.append(ch)
        elif ch in {"-", "_", " ", "/", "\\"}:
            cleaned.append("-")
    slug = "".join(cleaned).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "artifact"


def level_artifacts_dir(root: str | Path, level_id: str, level_name: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path(root) / f"{level_id}-{safe_slug(level_name)}" / stamp
    path.mkdir(parents=True, exist_ok=True)
    return path


def open_path(path: str | Path) -> None:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True) if not p.suffix else p.parent.mkdir(parents=True, exist_ok=True)
    if sys.platform.startswith("win"):
        os.startfile(str(p))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(p)])
    else:
        subprocess.Popen(["xdg-open", str(p)])
