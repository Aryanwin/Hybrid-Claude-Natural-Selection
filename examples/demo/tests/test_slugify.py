import pytest

from mypkg.text import normalize_whitespace, slugify


def test_basic_words_joined_by_dash():
    assert slugify("Hello World") == "hello-world"


def test_punctuation_is_removed():
    assert slugify("Hello, World! How's it going?") == "hello-world-hows-it-going"


def test_accents_become_ascii():
    assert slugify("Crème Brûlée à la carte") == "creme-brulee-a-la-carte"


def test_non_latin_characters_dropped():
    assert slugify("Tokyo 東京 guide") == "tokyo-guide"


def test_repeated_separators_collapse():
    assert slugify("  a --- b __ c  ") == "a-b-c"


def test_numbers_kept():
    assert slugify("Top 10 Tips for 2026") == "top-10-tips-for-2026"


def test_empty_and_symbol_only_give_empty_string():
    assert slugify("") == ""
    assert slugify("!!! ???") == ""


def test_max_length_cuts_on_word_boundary():
    title = "the quick brown fox jumps over the lazy dog and keeps running far away"
    out = slugify(title)
    assert len(out) <= 60
    assert not out.endswith("-")
    assert title.replace(" ", "-").startswith(out)
    assert out == "the-quick-brown-fox-jumps-over-the-lazy-dog-and-keeps"


def test_single_long_word_is_hard_cut():
    assert slugify("a" * 100) == "a" * 60


def test_custom_max_len():
    assert slugify("one two three", max_len=7) == "one-two"


def test_rejects_non_string():
    with pytest.raises(TypeError):
        slugify(None)


def test_existing_helper_unchanged():
    assert normalize_whitespace("  a \n b  ") == "a b"
