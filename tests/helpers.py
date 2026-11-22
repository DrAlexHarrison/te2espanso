"""Shared helpers. Expected values are hardcoded in each test module so the
oracle stays independent of the parser under test."""
from pathlib import Path

import yaml

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def load_matches(yml_path):
    """Load an Espanso YAML file and return [(trigger, replace), ...]."""
    data = yaml.safe_load(Path(yml_path).read_text(encoding="utf-8"))
    assert data is not None, f"empty YAML in {yml_path}"
    matches = data.get("matches")
    assert matches is not None, f"no 'matches' key in {yml_path}"
    result = []
    for entry in matches:
        trigger = entry.get("trigger")
        replace = entry.get("replace")
        assert isinstance(trigger, str), (
            f"trigger must load as str, got {type(trigger).__name__}: {trigger!r}"
        )
        assert isinstance(replace, str), (
            f"replace must load as str, got {type(replace).__name__}: {replace!r}"
        )
        result.append((trigger, replace))
    return result


def assert_round_trip(yml_path, expected, prefix=""):
    """Check a generated YAML file against hardcoded (trigger, content)."""
    want = [(f"{prefix}{t}" if prefix else t, c) for t, c in expected]
    got = load_matches(yml_path)
    assert len(got) == len(want), (
        f"count mismatch: got {len(got)} {got!r}, want {len(want)} {want!r}"
    )
    for (gt, gr), (wt, wr) in zip(got, want):
        assert gt == wt, f"trigger mismatch: got {gt!r}, want {wt!r}"
        assert gr == wr, (
            f"replace mismatch for trigger {wt!r}: got {gr!r}, want {wr!r}"
        )
