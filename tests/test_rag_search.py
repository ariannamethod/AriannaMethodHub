import numpy as np

from arianna_core.rag import load_corpus, rag_search


def test_load_corpus_and_search(tmp_path):
    doc = tmp_path / "doc.txt"
    doc.write_text("Hello world.\n\nAnother line.", encoding="utf-8")
    db = tmp_path / "vecs.db"
    load_corpus([str(doc)], db_path=str(db), dim=32)
    np.random.seed(0)
    results = rag_search("hello", k=1, min_score=0.1, db_path=str(db))
    assert results
    top = results[0]
    assert top["path"] == str(doc)
    assert top["lines"] == (1, 1)
    assert "Hello world." in top["snippet"]
