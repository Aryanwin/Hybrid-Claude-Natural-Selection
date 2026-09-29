from autocomplete import Autocomplete


def make():
    ac = Autocomplete()
    for w, n in [("apple", 10), ("apricot", 5), ("app", 5), ("banana", 3), ("apex", 1)]:
        ac.add(w, n)
    return ac


def test_ranked_by_weight_then_alpha():
    assert make().suggest("ap") == ["apple", "app", "apricot", "apex"]


def test_k_limit_and_default():
    ac = make()
    assert ac.suggest("a", 2) == ["apple", "app"]
    for i in range(10):
        ac.add(f"z{i}")
    assert len(ac.suggest("z")) == 5


def test_weights_accumulate():
    ac = make()
    ac.add("apex", 20)
    assert ac.suggest("ap", 1) == ["apex"]


def test_case_insensitive():
    ac = Autocomplete()
    ac.add("Hello", 2)
    ac.add("HELLO")
    ac.add("help", 2)
    assert ac.suggest("HE") == ["hello", "help"]


def test_no_match_and_empty_prefix():
    ac = make()
    assert ac.suggest("zz") == []
    assert ac.suggest("", 3) == ["apple", "app", "apricot"]


def test_remove():
    ac = make()
    assert ac.remove("APPLE") is True
    assert ac.remove("apple") is False
    assert "apple" not in ac.suggest("ap")
