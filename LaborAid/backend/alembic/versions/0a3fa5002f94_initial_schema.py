"""initial schema

Revision ID: 0a3fa5002f94
Revises:
Create Date: 2026-05-14 18:57:47.941959
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '0a3fa5002f94'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── teams ─────────────────────────────────────────────────────────────────
    op.create_table(
        'teams',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_teams_owner_id', 'teams', ['owner_id'], unique=False)

    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('team_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
    )
    op.create_index('ix_users_role', 'users', ['role'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # ── cases ─────────────────────────────────────────────────────────────────
    op.create_table(
        'cases',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('case_number', sa.String(length=100), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('case_type', sa.String(length=50), nullable=False),
        sa.Column('court', sa.String(length=200), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=True),
        sa.Column('plaintiff', sa.Text(), nullable=True),
        sa.Column('defendant', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=True),
        sa.Column('filing_date', sa.String(length=20), nullable=True),
        sa.Column('hearing_dates', sa.JSON(), nullable=True),
        sa.Column('deadline_dates', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_cases_owner_id', 'cases', ['owner_id'], unique=False)
    op.create_index('ix_cases_status', 'cases', ['status'], unique=False)

    # ── templates ─────────────────────────────────────────────────────────────
    op.create_table(
        'templates',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('structure', sa.JSON(), nullable=False),
        sa.Column('ai_prompt', sa.Text(), nullable=False),
        sa.Column('format_rules', sa.JSON(), nullable=True),
        sa.Column('variables', sa.JSON(), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=True),
        sa.Column('owner_id', sa.Integer(), nullable=True),
        sa.Column('team_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_templates_owner_id', 'templates', ['owner_id'], unique=False)
    op.create_index('ix_templates_type', 'templates', ['type'], unique=False)

    # ── documents ─────────────────────────────────────────────────────────────
    op.create_table(
        'documents',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('case_id', sa.Integer(), nullable=True),
        sa.Column('template_id', sa.Integer(), nullable=True),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('ai_metadata', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('version', sa.Integer(), nullable=True),
        sa.Column('exported_path', sa.String(length=500), nullable=True),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['template_id'], ['templates.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_documents_case_id', 'documents', ['case_id'], unique=False)
    op.create_index('ix_documents_owner_id', 'documents', ['owner_id'], unique=False)
    op.create_index('ix_documents_status', 'documents', ['status'], unique=False)

    # ── evidences ─────────────────────────────────────────────────────────────
    op.create_table(
        'evidences',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('case_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=True),
        sa.Column('ocr_text', sa.Text(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=True),
        sa.Column('analysis', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_evidences_case_id', 'evidences', ['case_id'], unique=False)

    # ── search_records ────────────────────────────────────────────────────────
    op.create_table(
        'search_records',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('case_id', sa.Integer(), nullable=True),
        sa.Column('query', sa.String(length=2000), nullable=False),
        sa.Column('result_type', sa.String(length=20), nullable=True),
        sa.Column('results', sa.JSON(), nullable=True),
        sa.Column('sources_used', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_search_records_case_id', 'search_records', ['case_id'], unique=False)
    op.create_index('ix_search_records_user_id', 'search_records', ['user_id'], unique=False)

    # ── knowledge_items ───────────────────────────────────────────────────────
    op.create_table(
        'knowledge_items',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('source', sa.String(length=200), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('embedding_id', sa.String(length=100), nullable=True),
        sa.Column('owner_id', sa.Integer(), nullable=True),
        sa.Column('team_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_knowledge_items_owner_id', 'knowledge_items', ['owner_id'], unique=False)

    # ── llm_settings ──────────────────────────────────────────────────────────
    op.create_table(
        'llm_settings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('base_url', sa.String(length=500), nullable=False),
        sa.Column('api_key', sa.String(length=500), nullable=False),
        sa.Column('model_name', sa.String(length=200), nullable=True),
        sa.Column('max_tokens', sa.Integer(), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_llm_settings_owner_id', 'llm_settings', ['owner_id'], unique=False)

    # ── contracts ─────────────────────────────────────────────────────────────
    op.create_table(
        'contracts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('case_id', sa.Integer(), nullable=True),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=True),
        sa.Column('file_type', sa.String(length=50), nullable=True),
        sa.Column('parsed_text', sa.Text(), nullable=True),
        sa.Column('clauses', sa.JSON(), nullable=True),
        sa.Column('review_report', sa.Text(), nullable=True),
        sa.Column('risk_items', sa.JSON(), nullable=True),
        sa.Column('risk_score', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_contracts_case_id', 'contracts', ['case_id'], unique=False)
    op.create_index('ix_contracts_owner_id', 'contracts', ['owner_id'], unique=False)
    op.create_index('ix_contracts_status', 'contracts', ['status'], unique=False)

    # ── research_reports ──────────────────────────────────────────────────────
    op.create_table(
        'research_reports',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('report', sa.Text(), nullable=False),
        sa.Column('sources_used', sa.JSON(), nullable=False),
        sa.Column('case_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── app_configs ───────────────────────────────────────────────────────────
    op.create_table(
        'app_configs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('config_key', sa.String(length=200), nullable=False),
        sa.Column('config_value', sa.Text(), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_app_configs_category', 'app_configs', ['category'], unique=False)
    op.create_index('ix_app_configs_owner_id', 'app_configs', ['owner_id'], unique=False)

    # ── external_api_configs ──────────────────────────────────────────────────
    op.create_table(
        'external_api_configs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=False),
        sa.Column('base_url', sa.String(length=1000), nullable=False),
        sa.Column('auth_type', sa.String(length=50), nullable=False),
        sa.Column('auth_token', sa.String(length=1000), nullable=False),
        sa.Column('auth_header_name', sa.String(length=200), nullable=False),
        sa.Column('auth_username', sa.String(length=200), nullable=False),
        sa.Column('auth_password', sa.String(length=500), nullable=False),
        sa.Column('custom_headers', sa.Text(), nullable=False),
        sa.Column('search_law_path', sa.String(length=500), nullable=False),
        sa.Column('search_law_method', sa.String(length=10), nullable=False),
        sa.Column('search_case_path', sa.String(length=500), nullable=False),
        sa.Column('search_case_method', sa.String(length=10), nullable=False),
        sa.Column('get_provision_path', sa.String(length=500), nullable=False),
        sa.Column('get_provision_method', sa.String(length=10), nullable=False),
        sa.Column('health_check_path', sa.String(length=500), nullable=False),
        sa.Column('response_mapping', sa.Text(), nullable=False),
        sa.Column('request_template', sa.Text(), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_external_api_configs_owner_id', 'external_api_configs', ['owner_id'], unique=False)


def downgrade() -> None:
    op.drop_table('external_api_configs')
    op.drop_table('app_configs')
    op.drop_table('research_reports')
    op.drop_table('contracts')
    op.drop_table('llm_settings')
    op.drop_table('knowledge_items')
    op.drop_table('search_records')
    op.drop_table('evidences')
    op.drop_table('documents')
    op.drop_table('templates')
    op.drop_table('cases')
    op.drop_table('users')
    op.drop_table('teams')
