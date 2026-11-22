"""Single-file, batch, and interactive modes plus prefix config round trip."""
import shutil
from pathlib import Path

import pytest

import te2espanso as te
from helpers import FIXTURES, load_matches
from test_csv import BASIC
from test_plist import GROUP_BASIC


def _setup_input_dir(tmp_path):
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    shutil.copy(FIXTURES / "basic.csv", input_dir / "basic.csv")
    shutil.copy(
        FIXTURES / "group_basic.textexpander",
        input_dir / "group_basic.textexpander",
    )
    return input_dir


def test_convert_file_unknown_extension(tmp_path):
    src = tmp_path / "notes.txt"
    src.write_text("hello", encoding="utf-8")
    assert te.convert_file(str(src), str(tmp_path / "out.yml")) == 0


def test_dry_run_writes_nothing(tmp_path):
    out = tmp_path / "out.yml"
    count = te.convert_file(str(FIXTURES / "basic.csv"), str(out), dry_run=True)
    assert count == len(BASIC)
    assert not out.exists()


def test_batch_convert(tmp_path):
    input_dir = _setup_input_dir(tmp_path)
    out_dir = tmp_path / "out"
    results = te.batch_convert(str(input_dir), str(out_dir), prefix="z")
    assert results == {
        "basic.csv": len(BASIC),
        "group_basic.textexpander": len(GROUP_BASIC),
    }
    got = load_matches(out_dir / "basic.yml")
    assert got == [(f"z{t}", c) for t, c in BASIC]
    got2 = load_matches(out_dir / "group_basic.yml")
    assert got2 == [(f"z{t}", c) for t, c in GROUP_BASIC]


def test_main_single_file(tmp_path, monkeypatch, capsys):
    out = tmp_path / "out.yml"
    monkeypatch.setattr(
        "sys.argv",
        ["te2espanso", str(FIXTURES / "basic.csv"), str(out), "--prefix", "rp"],
    )
    te.main()
    assert load_matches(out) == [(f"rp{t}", c) for t, c in BASIC]


def test_main_single_file_requires_output(monkeypatch):
    monkeypatch.setattr("sys.argv", ["te2espanso", str(FIXTURES / "basic.csv")])
    with pytest.raises(SystemExit) as exc:
        te.main()
    assert exc.value.code == 1


def test_main_batch_requires_output_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "sys.argv", ["te2espanso", "--batch", str(tmp_path), "--prefix", "x"]
    )
    with pytest.raises(SystemExit) as exc:
        te.main()
    assert exc.value.code == 1


def test_prefix_config_round_trip(tmp_path):
    config = tmp_path / "prefixes.conf"
    original = {"a.csv": "rp", "b.textexpander": "", "c.csv": "BLANK"}
    te.save_prefixes_config(config, original)
    assert te.load_prefixes_config(config) == original


def test_interactive_convert_and_use_config(tmp_path, monkeypatch):
    input_dir = _setup_input_dir(tmp_path)
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))

    # Discovery sorts by path: basic.csv before group_basic.textexpander.
    answers = iter(["rp", "BLANK"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))

    te.interactive_convert(str(input_dir))

    ready = fake_home / ".config" / "espanso" / "match" / "te-imports"
    staging = fake_home / ".config" / "espanso" / "te-imports-staging"
    assert load_matches(ready / "basic.yml") == [(f"rp{t}", c) for t, c in BASIC]
    # BLANK group goes to staging with no prefix.
    assert load_matches(staging / "group_basic.yml") == GROUP_BASIC

    saved = te.load_prefixes_config(input_dir / "prefixes.conf")
    assert saved == {"basic.csv": "rp", "group_basic.textexpander": "BLANK"}

    # Second run with --use-config must not prompt at all.
    (ready / "basic.yml").unlink()
    (staging / "group_basic.yml").unlink()

    def _fail_input(prompt=""):
        raise AssertionError("input() called during --use-config run")

    monkeypatch.setattr("builtins.input", _fail_input)
    te.interactive_convert(str(input_dir), use_config=True)
    assert load_matches(ready / "basic.yml") == [(f"rp{t}", c) for t, c in BASIC]
    assert load_matches(staging / "group_basic.yml") == GROUP_BASIC


def test_interactive_empty_dir(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    te.interactive_convert(str(tmp_path))
    assert "No .textexpander or .csv files found" in capsys.readouterr().out


def test_interactive_blank_prefix_means_no_prefix(tmp_path, monkeypatch):
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    shutil.copy(FIXTURES / "basic.csv", input_dir / "basic.csv")
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setattr("builtins.input", lambda prompt="": "")
    te.interactive_convert(str(input_dir))
    ready = fake_home / ".config" / "espanso" / "match" / "te-imports"
    assert load_matches(ready / "basic.yml") == BASIC
    saved = te.load_prefixes_config(input_dir / "prefixes.conf")
    assert saved == {"basic.csv": ""}


def test_discover_finds_nested(tmp_path):
    input_dir = _setup_input_dir(tmp_path)
    nested = input_dir / "sub"
    nested.mkdir()
    shutil.copy(FIXTURES / "group_te2.textexpander", nested / "group_te2.textexpander")
    found = te.discover_te_files(str(input_dir))
    names = sorted(Path(f).name for f, *_ in found)
    assert names == ["basic.csv", "group_basic.textexpander", "group_te2.textexpander"]
