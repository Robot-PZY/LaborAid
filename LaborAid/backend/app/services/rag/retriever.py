"""统一 RAG 检索层 -- LangChain 风格的 Retriever 封装。

第一阶段目标：
- 封装现有 ChromaDB 检索为 Retriever 接口
- 支持混合检索（向量 + BM25 关键词）
- 提供统一 API 供 research / docgen / search 调用
- 便于后续扩展 Reranker、Graph-RAG 等
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.services.vector.store import get_vector_service

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """统一检索结果条目。"""
    id: str
    content: str
    score: float
    source: str  # "vector" | "bm25" | "hybrid"
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "score": self.score,
            "source": self.source,
            "metadata": self.metadata,
        }


class BaseRetriever(ABC):
    """检索器基类 -- 兼容 LangChain Retriever 接口。"""

    @abstractmethod
    async def aget_relevant_documents(self, query: str, top_k: int = 10) -> list[RetrievalResult]:
        """异步检索相关文档。"""
        ...

    async def ainvoke(self, query: str, config: dict | None = None) -> list[RetrievalResult]:
        """LangChain 风格调用入口。"""
        top_k = (config or {}).get("top_k", 10)
        return await self.aget_relevant_documents(query, top_k)


class ChromaRetriever(BaseRetriever):
    """ChromaDB 向量检索器 -- 封装现有 VectorStoreService。"""

    def __init__(self, collection: str = "cases"):
        """
        Args:
            collection: "cases" | "statutes" | "knowledge"
        """
        self._collection = collection

    async def aget_relevant_documents(self, query: str, top_k: int = 10) -> list[RetrievalResult]:
        svc = get_vector_service()
        if self._collection == "cases":
            raw = await svc.search_cases(query, top_k=top_k)
        elif self._collection == "statutes":
            raw = await svc.search_statutes(query, top_k=top_k)
        elif self._collection == "knowledge":
            raw = await svc.search_knowledge(query, top_k=top_k)
        else:
            logger.warning("Unknown collection: %s", self._collection)
            return []

        return [
            RetrievalResult(
                id=item.get("id", ""),
                content=item.get("content", ""),
                score=1.0 - (item.get("distance", 0) / 2),  # cosine distance → similarity
                source="vector",
                metadata=item.get("metadata", {}),
            )
            for item in raw
        ]


class BM25Retriever(BaseRetriever):
    """BM25 关键词检索器 -- 从数据库加载文本语料。

    注意：BM25 索引在首次查询时构建，后续复用。
    生产环境建议预热索引或定期重建。
    """

    def __init__(self, corpus_source: str = "knowledge_db"):
        """
        Args:
            corpus_source: "knowledge_db" | "cases_db"
        """
        self._corpus_source = corpus_source
        self._index = None
        self._docs: list[dict] = []

    async def _build_index(self):
        """异步构建 BM25 索引（懒加载）。"""
        if self._index is not None:
            return

        try:
            from rank_bm25 import BM25Okapi
            import jieba
        except ImportError:
            logger.warning("rank_bm25 or jieba not installed, BM25Retriever disabled")
            return

        # 加载语料（异步）
        self._docs = await self._load_corpus()
        if not self._docs:
            logger.info("BM25 corpus is empty for source=%s", self._corpus_source)
            return

        # 分词
        tokenized = [
            list(jieba.cut(f"{d.get('title', '')} {d.get('content', '')}"))
            for d in self._docs
        ]
        self._index = BM25Okapi(tokenized)
        logger.info("BM25 index built: source=%s, docs=%d", self._corpus_source, len(self._docs))

    async def _load_corpus(self) -> list[dict]:
        """从数据库加载语料（异步）。"""
        docs: list[dict] = []
        try:
            from app.core.database import async_session
            from sqlalchemy import select

            async with async_session() as session:
                if self._corpus_source == "knowledge_db":
                    from app.models.knowledge import KnowledgeItem
                    result = await session.execute(
                        select(KnowledgeItem).where(KnowledgeItem.is_platform.is_(True))
                    )
                    for item in result.scalars().all():
                        docs.append({
                            "id": str(item.id),
                            "title": item.title or "",
                            "content": item.content or "",
                            "metadata": {"source": item.source or "", "tags": item.tags or []},
                        })
                elif self._corpus_source == "cases_db":
                    from app.models.case import Case
                    result = await session.execute(select(Case).limit(5000))
                    for case in result.scalars().all():
                        docs.append({
                            "id": str(case.id),
                            "title": case.title or "",
                            "content": case.description or "",
                            "metadata": {"case_type": case.case_type or "", "status": case.status or ""},
                        })
        except Exception as e:
            logger.error("BM25 corpus load failed: %s", e)
        return docs

    async def aget_relevant_documents(self, query: str, top_k: int = 10) -> list[RetrievalResult]:
        # 懒加载索引
        if self._index is None:
            await asyncio.to_thread(self._build_index)

        if self._index is None or not self._docs:
            return []

        try:
            import jieba
            tokens = list(jieba.cut(query))
            scores = self._index.get_scores(tokens)

            # 取 top_k
            top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
            results: list[RetrievalResult] = []
            for idx in top_indices:
                if scores[idx] > 0:
                    doc = self._docs[idx]
                    results.append(RetrievalResult(
                        id=doc["id"],
                        content=doc["content"][:500],  # 截断避免过长
                        score=float(scores[idx]),
                        source="bm25",
                        metadata=doc.get("metadata", {}),
                    ))
            return results
        except Exception as e:
            logger.warning("BM25 search failed: %s", e)
            return []


class EnsembleRetriever(BaseRetriever):
    """混合检索器 -- 融合向量检索与 BM25 关键词检索。

    采用 Reciprocal Rank Fusion (RRF) 策略合并结果。
    """

    def __init__(
        self,
        retrievers: list[BaseRetriever],
        weights: list[float] | None = None,
        rrf_k: int = 60,
    ):
        """
        Args:
            retrievers: 子检索器列表
            weights: 各检索器权重（默认等权）
            rrf_k: RRF 公式中的常数 k（默认 60）
        """
        self._retrievers = retrievers
        self._weights = weights or [1.0] * len(retrievers)
        self._rrf_k = rrf_k

    async def aget_relevant_documents(self, query: str, top_k: int = 10) -> list[RetrievalResult]:
        # 并行调用所有子检索器
        tasks = [r.aget_relevant_documents(query, top_k=top_k * 2) for r in self._retrievers]
        all_results = await asyncio.gather(*tasks, return_exceptions=True)

        # RRF 融合
        score_map: dict[str, float] = {}
        result_map: dict[str, RetrievalResult] = {}

        for retriever_idx, results in enumerate(all_results):
            if isinstance(results, Exception):
                logger.warning("Retriever %d failed: %s", retriever_idx, results)
                continue

            weight = self._weights[retriever_idx]
            for rank, item in enumerate(results):
                doc_id = item.id
                # RRF: score += weight / (k + rank)
                rrf_score = weight / (self._rrf_k + rank + 1)
                score_map[doc_id] = score_map.get(doc_id, 0) + rrf_score

                # 保留最高分对应的原始结果
                if doc_id not in result_map or score_map[doc_id] > result_map[doc_id].score:
                    result_map[doc_id] = RetrievalResult(
                        id=item.id,
                        content=item.content,
                        score=score_map[doc_id],
                        source="hybrid",
                        metadata={**item.metadata, "rrf_score": score_map[doc_id]},
                    )

        # 按 RRF 分数排序，取 top_k
        sorted_ids = sorted(score_map.keys(), key=lambda x: score_map[x], reverse=True)[:top_k]
        return [result_map[doc_id] for doc_id in sorted_ids]


# ── 工厂函数 ──────────────────────────────────────────────────────────────

def get_statutes_retriever(hybrid: bool = True) -> BaseRetriever:
    """获取法条检索器。

    Args:
        hybrid: True=混合检索（向量+BM25），False=仅向量
    """
    vector = ChromaRetriever(collection="statutes")
    if not hybrid:
        return vector

    bm25 = BM25Retriever(corpus_source="knowledge_db")  # TODO: 专用法条语料
    return EnsembleRetriever(
        retrievers=[vector, bm25],
        weights=[0.7, 0.3],  # 向量权重更高
    )


def get_cases_retriever(hybrid: bool = True) -> BaseRetriever:
    """获取案例检索器。"""
    vector = ChromaRetriever(collection="cases")
    if not hybrid:
        return vector

    bm25 = BM25Retriever(corpus_source="cases_db")
    return EnsembleRetriever(
        retrievers=[vector, bm25],
        weights=[0.7, 0.3],
    )


def get_knowledge_retriever(hybrid: bool = True) -> BaseRetriever:
    """获取知识库检索器。"""
    vector = ChromaRetriever(collection="knowledge")
    if not hybrid:
        return vector

    bm25 = BM25Retriever(corpus_source="knowledge_db")
    return EnsembleRetriever(
        retrievers=[vector, bm25],
        weights=[0.6, 0.4],  # 知识库更均衡
    )


# ── 便捷函数 ──────────────────────────────────────────────────────────────

async def retrieve_statutes(query: str, top_k: int = 5, hybrid: bool = True) -> list[RetrievalResult]:
    """检索相关法条。"""
    retriever = get_statutes_retriever(hybrid=hybrid)
    return await retriever.ainvoke(query, config={"top_k": top_k})


async def retrieve_cases(query: str, top_k: int = 5, hybrid: bool = True) -> list[RetrievalResult]:
    """检索相关案例。"""
    retriever = get_cases_retriever(hybrid=hybrid)
    return await retriever.ainvoke(query, config={"top_k": top_k})


async def retrieve_knowledge(query: str, top_k: int = 5, hybrid: bool = True) -> list[RetrievalResult]:
    """检索知识库。"""
    retriever = get_knowledge_retriever(hybrid=hybrid)
    return await retriever.ainvoke(query, config={"top_k": top_k})
