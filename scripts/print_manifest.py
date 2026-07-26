from __future__ import annotations
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from levelupdiag_core.manifest import list_levels
for level in list_levels(ROOT):
    print(f"{level.id} | {level.name} | {level.file} | release_blocking={level.blocking_for_release}")
