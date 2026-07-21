from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '19738b8da770'
down_revision: Union[str, None] = '472877f5ea5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('campaigns', sa.Column('start_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('campaigns', sa.Column('max_team_size', sa.Integer(), nullable=False, server_default='4'))
    op.add_column('campaigns', sa.Column('max_submissions_per_team', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('campaigns', sa.Column('allow_late_submissions', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column('campaigns', 'allow_late_submissions')
    op.drop_column('campaigns', 'max_submissions_per_team')
    op.drop_column('campaigns', 'max_team_size')
    op.drop_column('campaigns', 'start_date')
