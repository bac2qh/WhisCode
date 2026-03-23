from pathlib import Path

from whiscode.hotwords import apply_replacements, load_hotwords


def test_load_hotwords_full(tmp_path):
    f = tmp_path / "hotwords.txt"
    f.write_text(
        "# A comment\n"
        "\n"
        "Invisalign\n"
        "WhisCode\n"
        "\n"
        "# Replacements\n"
        "foo -> bar\n"
        "hello world -> goodbye\n"
    )
    words, replacements = load_hotwords(f)
    assert words == ["Invisalign", "WhisCode"]
    assert replacements == {"foo": "bar", "hello world": "goodbye"}


def test_load_hotwords_missing_file(tmp_path):
    words, replacements = load_hotwords(tmp_path / "nope.txt")
    assert words == []
    assert replacements == {}


def test_load_hotwords_empty_file(tmp_path):
    f = tmp_path / "hotwords.txt"
    f.write_text("# only comments\n\n")
    words, replacements = load_hotwords(f)
    assert words == []
    assert replacements == {}


def test_apply_replacements_case_insensitive():
    result = apply_replacements("I said Hello to HELLO", {"hello": "hi"})
    assert result == "I said hi to hi"


def test_apply_replacements_empty():
    assert apply_replacements("unchanged", {}) == "unchanged"


def test_apply_replacements_multiple():
    result = apply_replacements("foo and bar", {"foo": "baz", "bar": "qux"})
    assert result == "baz and qux"
