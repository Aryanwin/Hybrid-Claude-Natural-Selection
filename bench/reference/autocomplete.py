class Autocomplete:
    def __init__(self):
        self.weights = {}

    def add(self, word, weight=1):
        w = word.lower()
        self.weights[w] = self.weights.get(w, 0) + weight

    def suggest(self, prefix, k=5):
        p = prefix.lower()
        hits = [w for w in self.weights if w.startswith(p)]
        return sorted(hits, key=lambda w: (-self.weights[w], w))[:k]

    def remove(self, word):
        return self.weights.pop(word.lower(), None) is not None
