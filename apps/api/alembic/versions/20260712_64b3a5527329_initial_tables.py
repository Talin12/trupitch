"""initial tables

Revision ID: 64b3a5527329
Revises:
Create Date: 2026-07-12 22:55:00.497460

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '64b3a5527329'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('organizers',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_organizers_email'), 'organizers', ['email'], unique=True)
    op.create_table('campaigns',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('organizer_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('deadline', sa.DateTime(timezone=True), nullable=False),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.ForeignKeyConstraint(['organizer_id'], ['organizers.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_campaigns_organizer_id'), 'campaigns', ['organizer_id'], unique=False)
    op.create_table('rules',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('campaign_id', sa.Integer(), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('weight', sa.Float(), nullable=False),
    sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_rules_campaign_id'), 'rules', ['campaign_id'], unique=False)
    op.create_table('submissions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('campaign_id', sa.Integer(), nullable=False),
    sa.Column('team_name', sa.String(length=255), nullable=False),
    sa.Column('github_url', sa.String(length=512), nullable=False),
    sa.Column('pitch_text', sa.Text(), nullable=False),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('final_score', sa.Float(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_submissions_campaign_id'), 'submissions', ['campaign_id'], unique=False)
    op.create_index(op.f('ix_submissions_status'), 'submissions', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_submissions_status'), table_name='submissions')
    op.drop_index(op.f('ix_submissions_campaign_id'), table_name='submissions')
    op.drop_table('submissions')
    op.drop_index(op.f('ix_rules_campaign_id'), table_name='rules')
    op.drop_table('rules')
    op.drop_index(op.f('ix_campaigns_organizer_id'), table_name='campaigns')
    op.drop_table('campaigns')
    op.drop_index(op.f('ix_organizers_email'), table_name='organizers')
    op.drop_table('organizers')
