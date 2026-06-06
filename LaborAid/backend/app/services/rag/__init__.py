"""统一 RAG 检索层 -- LangChain 风格 Retriever 封装。

提供混合检索（向量 + BM25）和 LCEL Pipeline 能力，供 research / docgen / search 统一调用。
"""

from app.services.rag.retriever import (
    BaseRetriever,
    BM25Retriever,
    ChromaRetriever,
    EnsembleRetriever,
    RetrievalResult,
    get_cases_retriever,
    get_knowledge_retriever,
    get_statutes_retriever,
    retrieve_cases,
    retrieve_knowledge,
    retrieve_statutes,
)

from app.services.rag.chains import (
    PipelineStatsCallback,
    build_query_decomposition_chain,
    build_research_synthesis_chain,
    build_deep_dive_analysis_chain,
    build_case_parsing_chain,
    build_document_generation_chain,
    build_quality_review_chain,
    build_research_pipeline,
    run_query_decomposition,
    run_research_pipeline,
    extract_json_from_text,
)

__all__ = [
    # Retriever
    "BaseRetriever",
    "BM25Retriever",
    "ChromaRetriever",
    "EnsembleRetriever",
    "RetrievalResult",
    "get_cases_retriever",
    "get_knowledge_retriever",
    "get_statutes_retriever",
    "retrieve_cases",
    "retrieve_knowledge",
    "retrieve_statutes",
    # Chains
    "PipelineStatsCallback",
    "build_query_decomposition_chain",
    "build_research_synthesis_chain",
    "build_deep_dive_analysis_chain",
    "build_case_parsing_chain",
    "build_document_generation_chain",
    "build_quality_review_chain",
    "build_research_pipeline",
    "run_query_decomposition",
    "run_research_pipeline",
    "extract_json_from_text",
]
