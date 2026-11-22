"""Native .textexpander (plist) inputs, TE2 + TE3 + JSON rich text."""
import json
import plistlib

import te2espanso as te
from helpers import FIXTURES, assert_round_trip

GROUP_BASIC = [
    ("sig", "Best regards,\nAlex"),
    ("trail2", "First line\nSecond line\n\n"),
    ("docs", "See the [docs](https://example.com/docs) first."),
    ("steps", "Steps:\n1. Open the app\n2. Click Save"),
    ("groceries", "• Milk\n• Eggs"),
    ("wrapup", "• Only item\nDone."),
    ("blanky", ""),
    ("uni", "Café ☕ — naïve résumé 🎉"),
]

GROUP_TE2 = [
    ("old1", "Legacy snippet one"),
    ("old2", ""),
]


def test_parse_te3_group():
    matches, name = te.parse_textexpander_file(
        str(FIXTURES / "group_basic.textexpander")
    )
    assert name == "Work Basics"
    assert matches == GROUP_BASIC


def test_parse_te2_group():
    matches, name = te.parse_textexpander_file(
        str(FIXTURES / "group_te2.textexpander")
    )
    assert name == "Legacy TE2"
    assert matches == GROUP_TE2


def test_te3_round_trip(tmp_path):
    out = tmp_path / "group.yml"
    count = te.convert_file(str(FIXTURES / "group_basic.textexpander"), str(out))
    assert count == len(GROUP_BASIC)
    assert_round_trip(out, GROUP_BASIC)


def test_te2_round_trip(tmp_path):
    out = tmp_path / "group2.yml"
    te.convert_file(str(FIXTURES / "group_te2.textexpander"), str(out))
    assert_round_trip(out, GROUP_TE2)


def test_te3_with_prefix(tmp_path):
    out = tmp_path / "group.yml"
    te.convert_file(
        str(FIXTURES / "group_basic.textexpander"), str(out), prefix="wk"
    )
    assert_round_trip(out, GROUP_BASIC, prefix="wk")


def test_binary_plist(tmp_path):
    src = tmp_path / "bin.textexpander"
    payload = {
        "groupInfo": {"groupName": "Binary Group"},
        "snippetsTE3": [
            {"abbreviation": "b1", "plainText": "from binary plist"},
            {"abbreviation": "b2", "plainText": "multi\nline\n"},
        ],
    }
    with open(src, "wb") as f:
        plistlib.dump(payload, f, fmt=plistlib.FMT_BINARY)
    out = tmp_path / "bin.yml"
    te.convert_file(str(src), str(out))
    assert_round_trip(out, [("b1", "from binary plist"), ("b2", "multi\nline\n")])


def test_plaintext_wins_over_json(tmp_path):
    # When both exist, plainText is authoritative (existing contract).
    src = tmp_path / "both.textexpander"
    payload = {
        "groupInfo": {"groupName": "Both"},
        "snippetsTE3": [
            {
                "abbreviation": "both",
                "plainText": "plain wins",
                "extraInfo": {
                    "jsonStr": json.dumps(
                        {"nodes": [{"e": "tx", "tx": "json loses"}]}
                    )
                },
            }
        ],
    }
    with open(src, "wb") as f:
        plistlib.dump(payload, f)
    matches, _ = te.parse_textexpander_file(str(src))
    assert matches == [("both", "plain wins")]


def _json(nodes):
    return te.parse_textexpander_json(json.dumps({"nodes": nodes}))


def test_json_single_paragraph_no_trailing_newline():
    assert _json([{"e": "p", "nodes": [{"e": "tx", "tx": "hello"}]}]) == "hello"


def test_json_two_paragraphs():
    nodes = [
        {"e": "p", "nodes": [{"e": "tx", "tx": "one"}]},
        {"e": "p", "nodes": [{"e": "tx", "tx": "two"}]},
    ]
    assert _json(nodes) == "one\ntwo"


def test_json_numbered_list():
    nodes = [
        {
            "e": "numbered-list",
            "list-items": [
                {"nodes": [{"e": "tx", "tx": "first"}]},
                {"nodes": [{"e": "tx", "tx": "second"}]},
            ],
        }
    ]
    assert _json(nodes) == "1. first\n2. second"


def test_json_bulleted_list_no_leading_newline():
    nodes = [
        {
            "e": "bulleted-list",
            "list-items": [{"nodes": [{"e": "tx", "tx": "only"}]}],
        }
    ]
    assert _json(nodes) == "• only"


def test_json_paragraph_then_list_single_separator():
    nodes = [
        {"e": "p", "nodes": [{"e": "tx", "tx": "Intro:"}]},
        {
            "e": "bulleted-list",
            "list-items": [{"nodes": [{"e": "tx", "tx": "item"}]}],
        },
    ]
    assert _json(nodes) == "Intro:\n• item"


def test_json_list_then_paragraph_not_merged():
    nodes = [
        {
            "e": "bulleted-list",
            "list-items": [{"nodes": [{"e": "tx", "tx": "item"}]}],
        },
        {"e": "p", "nodes": [{"e": "tx", "tx": "After."}]},
    ]
    assert _json(nodes) == "• item\nAfter."


def test_json_br_and_inline_link():
    nodes = [
        {"e": "tx", "tx": "a"},
        {"e": "br"},
        {"e": "tx", "tx": "b"},
    ]
    assert _json(nodes) == "a\nb"


def test_json_link_url_only():
    nodes = [{"e": "link", "url": "https://example.com", "nodes": []}]
    assert _json(nodes) == "https://example.com"


def test_json_malformed_returns_empty():
    assert te.parse_textexpander_json("{not json") == ""


def test_corrupt_plist_returns_empty(tmp_path):
    src = tmp_path / "bad.textexpander"
    src.write_bytes(b"not a plist at all")
    matches, name = te.parse_textexpander_file(str(src))
    assert matches == []
    assert name == ""
