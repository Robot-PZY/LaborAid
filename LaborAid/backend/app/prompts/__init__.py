"""LaborAid prompt templates and persona."""

from app.prompts.persona import (
    LABORAID_PERSONA,
    DEFAULT_LAWYER_ROLE,
    PLAIN_LANGUAGE_HINT,
    build_system,
    lawyer_system,
    prompt_with_persona,
    SYSTEM_CONTRACT,
    SYSTEM_CROSS_EXAM,
    SYSTEM_DOCUMENT,
    SYSTEM_DOCUMENT_BUNDLE,
    SYSTEM_DOCUMENT_REVIEW,
    SYSTEM_EVIDENCE,
    SYSTEM_RESEARCH,
    SYSTEM_SEARCH,
)

__all__ = [
    "LABORAID_PERSONA",
    "DEFAULT_LAWYER_ROLE",
    "PLAIN_LANGUAGE_HINT",
    "build_system",
    "lawyer_system",
    "prompt_with_persona",
    "SYSTEM_CONTRACT",
    "SYSTEM_CROSS_EXAM",
    "SYSTEM_DOCUMENT",
    "SYSTEM_DOCUMENT_BUNDLE",
    "SYSTEM_DOCUMENT_REVIEW",
    "SYSTEM_EVIDENCE",
    "SYSTEM_RESEARCH",
    "SYSTEM_SEARCH",
]
