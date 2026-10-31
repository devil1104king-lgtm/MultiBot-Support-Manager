"""Unit tests for helper functions."""

from utils.helpers import escape_html, mask_token, status_emoji, truncate


def test_mask_token():
    assert mask_token("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11") == "123456:A...ew11"
    assert mask_token("short") == "***"


def test_escape_html():
    assert escape_html("<b>hi</b>") == "&lt;b&gt;hi&lt;/b&gt;"
    assert escape_html("a & b") == "a &amp; b"


def test_status_emoji():
    assert status_emoji(True) == "🟢"
    assert status_emoji(False) == "🔴"


def test_truncate():
    assert truncate("hello", 10) == "hello"
    assert truncate("abcdefghij", 5) == "abcd…"
