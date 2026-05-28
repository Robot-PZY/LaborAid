"""add composite indexes

Revision ID: b7c2e1d8f5a3
Revises: 0a3fa5002f94
Create Date: 2026-05-15 12:00:00.000000
"""
from typing import Sequence, Union
from alembic import op


revision: str = 'b7c2e1d8f5a3'
down_revision: Union[str, None] = '0a3fa5002f94'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── cases: composite indexes ──────────────────────────────────────────────
    op.create_index('ix_cases_owner_status', 'cases', ['owner_id', 'status'])
    op.create_index('ix_cases_owner_type', 'cases', ['owner_id', 'case_type'])
    op.create_index('ix_cases_team_id', 'cases', ['team_id'])
    op.create_index('ix_cases_team_status', 'cases', ['team_id', 'status'])

    # ── documents: composite indexes ──────────────────────────────────────────
    op.create_index('ix_documents_owner_case', 'documents', ['owner_id', 'case_id'])
    op.create_index('ix_documents_owner_type', 'documents', ['owner_id', 'type'])
    op.create_index('ix_documents_case_status', 'documents', ['case_id', 'status'])

    # ── evidences: composite indexes ──────────────────────────────────────────
    op.create_index('ix_evidences_case_sort', 'evidences', ['case_id', 'sort_order'])

    # ── knowledge_items: composite indexes ────────────────────────────────────
    op.create_index('ix_knowledge_items_team_id', 'knowledge_items', ['team_id'])
    op.create_index('ix_knowledge_items_owner_title', 'knowledge_items', ['owner_id', 'title'])


def downgrade() -> None:
    # ── knowledge_items ───────────────────────────────────────────────────────
    op.drop_index('ix_knowledge_items_owner_title', table_name='knowledge_items')
    op.drop_index('ix_knowledge_items_team_id', table_name='knowledge_items')

    # ── evidences ─────────────────────────────────────────────────────────────
    op.drop_index('ix_evidences_case_sort', table_name='evidences')

    # ── documents ─────────────────────────────────────────────────────────────
    op.drop_index('ix_documents_case_status', table_name='documents')
    op.drop_index('ix_documents_owner_type', table_name='documents')
    op.drop_index('ix_documents_owner_case', table_name='documents')

    # ── cases ─────────────────────────────────────────────────────────────────
    op.drop_index('ix_cases_team_status', table_name='cases')
    op.drop_index('ix_cases_team_id', table_name='cases')
    op.drop_index('ix_cases_owner_type', table_name='cases')
    op.drop_index('ix_cases_owner_status', table_name='cases')
