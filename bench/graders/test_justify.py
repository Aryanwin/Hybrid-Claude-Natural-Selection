import pytest
from justify import justify


def test_classic():
    words = "This is an example of text justification.".split()
    assert justify(words, 16) == ["This    is    an", "example  of text", "justification.  "]


def test_uneven_gaps_go_left():
    words = "What must be acknowledgment shall be".split()
    assert justify(words, 16) == ["What   must   be", "acknowledgment  ", "shall be        "]


def test_longer_text():
    words = ("Science is what we understand well enough to explain to a computer. "
             "Art is everything else we do").split()
    assert justify(words, 20) == [
        "Science  is  what we", "understand      well", "enough to explain to", "a  computer.  Art is",
        "everything  else  we", "do                  "]


def test_every_line_has_width():
    words = ("lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor").split()
    assert all(len(line) == 12 for line in justify(words, 12))


def test_single_word_and_exact_fit():
    assert justify(["word"], 10) == ["word      "]
    assert justify(["abc", "de"], 6) == ["abc de"]


def test_empty():
    assert justify([], 10) == []


def test_word_too_long():
    with pytest.raises(ValueError):
        justify(["short", "waytoolongword"], 10)
