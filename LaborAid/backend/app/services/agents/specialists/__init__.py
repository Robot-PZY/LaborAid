from app.services.agents.specialists.docgen import DocgenAgent
from app.services.agents.specialists.evidence import EvidenceAgent
from app.services.agents.specialists.guidance import GuidanceAgent
from app.services.agents.specialists.records import RecordsAgent
from app.services.agents.specialists.research import ResearchAgent

PIPELINE_AGENTS: list = [
    GuidanceAgent(),
    EvidenceAgent(),
    DocgenAgent(),
    ResearchAgent(),
    RecordsAgent(),
]

__all__ = ["PIPELINE_AGENTS"]
