from levenshtein import closest, edit_distance


def test_identical_and_empty():
    assert edit_distance("abc", "abc") == 0
    assert edit_distance("", "abc") == 3
    assert edit_distance("abc", "") == 3
    assert edit_distance("", "") == 0


def test_classic():
    assert edit_distance("kitten", "sitting") == 3
    assert edit_distance("flaw", "lawn") == 2
    assert edit_distance("intention", "execution") == 5


def test_symmetric():
    assert edit_distance("sunday", "saturday") == edit_distance("saturday", "sunday") == 3


def test_closest():
    assert closest("appel", ["apple", "apply", "ape"]) == "apple"


def test_closest_tie_earliest():
    assert closest("cat", ["bat", "hat", "cast"]) == "bat"


def test_closest_empty():
    assert closest("x", []) is None


def test_long_strings_fast():
    assert edit_distance("a" * 400, "b" * 400) == 400
