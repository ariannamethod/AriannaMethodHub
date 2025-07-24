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

