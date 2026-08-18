from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from levelupdiag_core.manifest import (
    CANONICAL_LEVEL_IDS,
    get_level,
    list_levels,
    load_manifest,
    normalize_level_id,
    validate_manifest,
)


ROOT = Path(__file__).resolve().parents[1]


def _manifest() -> dict:
    return json.loads((ROOT / "levelupdiag_manifest.json").read_text(encoding="utf-8"))


def test_normalize_level_number() -> None:
    assert normalize_level_id("4") == "N04"
    assert normalize_level_id("n4") == "N04"
    assert normalize_level_id("LUD-4") == "N04"


def test_normalize_invalid_level_fails() -> None:
    with pytest.raises(ValueError):
        normalize_level_id("contracts")


def test_versioned_manifest_has_exact_canonical_taxonomy() -> None:
    data = load_manifest(ROOT)
    assert validate_manifest(data) == []
    levels = list_levels(ROOT)
    assert tuple(level.id for level in levels) == CANONICAL_LEVEL_IDS
    assert get_level("4", ROOT).id == "N04"
    assert get_level("N11", ROOT).file == "levels/N11_delivery.pyw"


def test_required_core_validation_levels_are_required() -> None:
    levels = {level.id: level for level in list_levels(ROOT)}
    for level_id in ("N01", "N02", "N03", "N04", "N05"):
        assert levels[level_id].required is True
    for level_id in ("N00", "N06", "N07", "N08", "N09", "N10", "N11"):
        assert levels[level_id].required is False


def test_duplicate_id_is_detected() -> None:
    data = _manifest()
    data["levels"][1]["id"] = "N00"
    errors = validate_manifest(data)
    assert any("duplicate level id: N00" in error for error in errors)


def test_unknown_dependency_is_detected() -> None:
    data = _manifest()
    data["levels"][5]["depends_on"] = ["N99"]
    errors = validate_manifest(data)
    assert any("depends on unknown level N99" in error for error in errors)


def test_invalid_structure_is_detected() -> None:
    data = _manifest()
    data["levels"][3]["enabled"] = "yes"
    data["levels"][3]["timeout_seconds"] = 0
    errors = validate_manifest(data)
    assert any("enabled must be a boolean" in error for error in errors)
    assert any("timeout_seconds must be a positive integer" in error for error in errors)


def test_cycle_is_detected() -> None:
    data = _manifest()
    data["levels"][1]["depends_on"] = ["N02"]
    errors = validate_manifest(data)
    assert any("dependency cycle detected" in error for error in errors)
