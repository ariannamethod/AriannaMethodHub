from arianna_core import local_rag


def test_basic_query(tmp_path):
    doc = tmp_path / "doc.txt"
    text = "Hello world.\n\nGoodbye world."
    doc.write_text(text, encoding="utf-8")
    snippets = local_rag.load_snippets([doc])
    search = local_rag.SimpleSearch(snippets)
    result = search.query("hello", top_k=1)
    assert result == ["Hello world."]


def test_query_no_match(tmp_path):
    doc = tmp_path / "doc.txt"
    doc.write_text("a b c", encoding="utf-8")
    snippets = local_rag.load_snippets([doc])
    search = local_rag.SimpleSearch(snippets)
    assert search.query("zzz") == []


def test_query_no_recompute(tmp_path, monkeypatch):
    doc = tmp_path / "doc.txt"
    doc.write_text("x y z", encoding="utf-8")
    snippets = local_rag.load_snippets([doc])
    count = {"n": 0}
    orig_vectorize = local_rag._vectorize

    def counting_vectorize(tokens):
        count["n"] += 1
        return orig_vectorize(tokens)

    monkeypatch.setattr(local_rag, "_vectorize", counting_vectorize)
    search = local_rag.SimpleSearch(snippets)
    assert count["n"] == len(snippets)

    search.query("x")
    search.query("y")
    assert count["n"] == len(snippets) + 2


def test_tokenize_and_dot():
    tokens = local_rag._tokenize("Hello, HELLO world!")
    assert tokens == ["hello", "hello", "world"]
    v1 = local_rag._vectorize(tokens)
    v2 = local_rag._vectorize(["hello", "test"])
    assert local_rag._dot(v1, v2) == 2
