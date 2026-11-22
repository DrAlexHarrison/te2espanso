"""Adversarial single-value round trips through write_espanso_yaml."""
import pytest

import te2espanso as te
from helpers import load_matches

CONTENTS = [
    "hello world",
    "meet at 3 # sharp",
    "trailing hash #",
    "Note: check this",
    "ends with colon:",
    "12345",
    "3.14",
    "12:30",
    "2024-01-15",
    "y",
    "n",
    "Yes",
    "OFF",
    "~",
    "null",
    "0x1A",
    ".inf",
    ".nan",
    "...",
    "a\tb",
    "a\rb",
    "a\r\nb",
    "line1\nline2",
    "line1\nline2\n",
    "line1\nline2\n\n",
    "line1\nline2\n\n\n",
    "\nhello",
    "\n",
    "\n\n",
    "  indented first\nsecond",
    "keep   \nnext",
    "a\n   \nb",
    "a\n\tTabbed line",
    "a\tb\nc\td",
    "",
    "   ",
    ":foo",
    "::",
    "- item",
    "? what",
    "a\u2028b",
    "a\u2029b",
    "ship it 🚀 done",
    'say "hello" loudly',
    "it's fine",
    '"fully double quoted"',
    "'fully single quoted'",
    "C:\\path\\to\\file",
    "back\\slash and \"quote\"",
    "@handle",
    "`code`",
    "%YAML directive-like",
    "#not-a-comment value",
    "&anchor and *alias",
    "!tag-like",
    "| pipe start",
    "> fold start",
    "{json: like}",
    "[1, 2, 3]",
    "multi\nline with: colon\nand # hash\n- dash line",
    "ends with space ",
    " leading space",
    "bell\x07char",
]


@pytest.mark.parametrize("content", CONTENTS)
def test_content_round_trip(tmp_path, content):
    out = tmp_path / "out.yml"
    te.write_espanso_yaml([("trig", content)], str(out))
    got = load_matches(out)
    assert got == [("trig", content)]


TRIGGERS = [
    "plain",
    "123",
    "12:30",
    "yes",
    ":foo",
    "::",
    "-x",
    "a # b",
    "`bt",
    "@at",
    "#tag",
    "a\tb",
    "..dots",
    "- leading dash space",
    "'quoted'",
]


@pytest.mark.parametrize("trigger", TRIGGERS)
def test_trigger_round_trip(tmp_path, trigger):
    out = tmp_path / "out.yml"
    te.write_espanso_yaml([(trigger, "content")], str(out))
    got = load_matches(out)
    assert got == [(trigger, "content")]


def test_prefix_backtick_round_trip(tmp_path):
    out = tmp_path / "out.yml"
    te.write_espanso_yaml([("sig", "hello")], str(out), prefix="`")
    assert load_matches(out) == [("`sig", "hello")]


def test_prefix_making_trigger_numeric_round_trip(tmp_path):
    out = tmp_path / "out.yml"
    te.write_espanso_yaml([("23", "hello")], str(out), prefix="1")
    assert load_matches(out) == [("123", "hello")]


def test_group_name_with_newline_does_not_break_yaml(tmp_path):
    import yaml

    out = tmp_path / "out.yml"
    te.write_espanso_yaml(
        [("sig", "hello")], str(out), group_name="Bad\nName: injected"
    )
    data = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert set(data.keys()) == {"matches"}
    assert load_matches(out) == [("sig", "hello")]


def test_escape_yaml_string_units():
    assert te.escape_yaml_string("a\\b") == "a\\\\b"
    assert te.escape_yaml_string('a"b') == 'a\\"b'
    assert te.escape_yaml_string("a\nb") == "a\\nb"
    assert te.escape_yaml_string("a\tb") == "a\\tb"
    assert te.escape_yaml_string("a\rb") == "a\\rb"
