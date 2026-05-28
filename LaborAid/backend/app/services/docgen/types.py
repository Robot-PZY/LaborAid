"""Canonical document type slugs and legacy aliases (frontend / intake)."""

DOC_TYPE_ALIASES: dict[str, str] = {
    "defense": "answer",
    "representation": "agency_opinion",
    "opinion": "legal_opinion",
    # Legacy UI types → closest supported template type
    "criminal_complaint": "complaint",
    "mediation": "contract",
}


def normalize_doc_type(doc_type: str | None) -> str | None:
    if not doc_type:
        return None
    key = doc_type.strip()
    return DOC_TYPE_ALIASES.get(key, key)
