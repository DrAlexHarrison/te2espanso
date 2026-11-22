"""CSV inputs: parse + convert + YAML round trip against hardcoded truth."""
import te2espanso as te
from helpers import FIXTURES, assert_round_trip

BASIC = [
    ("sig", "Best regards, Alex"),
    ("addr", "Line one\nLine two\nLine three"),
    ("addr-trail", "First\nSecond\n"),
    ("addr-trail2", "First\nSecond\n\n"),
    ("site", "https://example.com/docs?a=1&b=2"),
    ("quote", 'She said "hello" loudly'),
    ("apos", "don't panic"),
    ("colon", "Note: check this"),
    ("empty", ""),
    ("dup", "first value"),
    ("dup", "second value"),
    ("emoji", "Ship it 🚀 — café ☕ ñandú"),
    ("tabbed", "col1\tcol2"),
]

SPECIALS = [
    ("sp-dash", "- leading dash"),
    ("sp-colon", ": leading colon"),
    ("sp-colon-nospace", ":nospace"),
    ("sp-question", "? question"),
    ("sp-hash", "# heading"),
    ("sp-amp", "&anchor text"),
    ("sp-star", "*alias text"),
    ("sp-bang", "!bang"),
    ("sp-pipe", "| pipe"),
    ("sp-gt", "> quoted"),
    ("sp-squote", "'single quoted'"),
    ("sp-dquote", '"double quoted"'),
    ("sp-percent", "%percent"),
    ("sp-at", "@mention"),
    ("sp-backtick", "`backtick code`"),
    ("`sig", "backtick trigger here"),
    (";date", "semicolon trigger"),
    ("..shrug", "dotdot trigger"),
    ("'tis", "leading apostrophe trigger"),
]

LOOKALIKES = [
    ("lk-int", "12345"),
    ("lk-float", "3.14"),
    ("lk-time", "12:30"),
    ("lk-date", "2024-01-15"),
    ("lk-yes", "yes"),
    ("lk-no", "No"),
    ("lk-y", "y"),
    ("lk-null", "~"),
    ("lk-hex", "0x1A"),
    ("lk-comment", "meet at 3 # sharp"),
    ("lk-dots", "..."),
    ("lk-bool", "true"),
    ("lk-url", "http://example.com:8080/path"),
    ("lk-backslash", "C:\\path\\to\\file"),
    ("lk-only-spaces", "   "),
]


def test_parse_csv_basic():
    assert te.parse_csv(str(FIXTURES / "basic.csv")) == BASIC


def test_parse_csv_specials():
    assert te.parse_csv(str(FIXTURES / "specials.csv")) == SPECIALS


def test_parse_csv_lookalikes():
    assert te.parse_csv(str(FIXTURES / "lookalikes.csv")) == LOOKALIKES


def test_csv_basic_round_trip(tmp_path):
    out = tmp_path / "basic.yml"
    count = te.convert_file(str(FIXTURES / "basic.csv"), str(out))
    assert count == len(BASIC)
    assert_round_trip(out, BASIC)


def test_csv_specials_round_trip(tmp_path):
    out = tmp_path / "specials.yml"
    te.convert_file(str(FIXTURES / "specials.csv"), str(out))
    assert_round_trip(out, SPECIALS)


def test_csv_lookalikes_round_trip(tmp_path):
    out = tmp_path / "lookalikes.yml"
    te.convert_file(str(FIXTURES / "lookalikes.csv"), str(out))
    assert_round_trip(out, LOOKALIKES)


def test_csv_with_prefix_round_trip(tmp_path):
    out = tmp_path / "basic.yml"
    te.convert_file(str(FIXTURES / "basic.csv"), str(out), prefix="rp")
    assert_round_trip(out, BASIC, prefix="rp")


def test_csv_bom_and_crlf(tmp_path):
    src = tmp_path / "bom.csv"
    src.write_bytes(b"\xef\xbb\xbfbomtrig,has bom\r\nother,plain\r\n")
    assert te.parse_csv(str(src)) == [("bomtrig", "has bom"), ("other", "plain")]


def test_csv_short_rows_skipped(tmp_path):
    src = tmp_path / "short.csv"
    src.write_text("lonely\noktrig,ok content\n", encoding="utf-8")
    assert te.parse_csv(str(src)) == [("oktrig", "ok content")]


def test_csv_trigger_whitespace_trimmed(tmp_path):
    # Documented normalization: abbreviations are trimmed (both parsers),
    # content is preserved exactly.
    src = tmp_path / "ws.csv"
    src.write_text("  padded  ,  content keeps spaces  \n", encoding="utf-8")
    assert te.parse_csv(str(src)) == [("padded", "  content keeps spaces  ")]
