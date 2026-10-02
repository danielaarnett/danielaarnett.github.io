"""Persistent publication vote totals and rolling IP cooldowns."""
from alembic import op
import sqlalchemy as sa

revision = 'a210b943ec82'
down_revision = 'f2190ab783c4'
branch_labels = None
depends_on = None


def upgrade():
    totals = op.create_table('publication_interest',
        sa.Column('slug', sa.String(120), primary_key=True),
        sa.Column('votes', sa.Integer(), nullable=False))
    op.create_table('publication_vote',
        sa.Column('book_slug', sa.String(120), sa.ForeignKey('publication_interest.slug'), primary_key=True),
        sa.Column('ip_hash', sa.String(64), primary_key=True),
        sa.Column('voted_at', sa.DateTime(), nullable=False))
    op.bulk_insert(totals, [{'slug': 'krampus', 'votes': 0}])


def downgrade():
    op.drop_table('publication_vote')
    op.drop_table('publication_interest')
