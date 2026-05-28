import pytest

from app.services.knowledge.crawler.chunker import split_law_articles


def test_split_law_articles_by_clause():
    text = """中华人民共和国测试法

第一条　为了测试，制定本法。

第二条　本法适用于测试场景。

第三条　测试应遵循诚实信用原则。"""
    chunks = split_law_articles(text, "中华人民共和国测试法")
    assert len(chunks) >= 3
    assert chunks[0][0].endswith("第一条")
    assert "为了测试" in chunks[0][1]
