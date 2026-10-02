"""Add independent publication voting for Orden na sdachu."""
from alembic import op
import sqlalchemy as sa

revision = 'b391ea42d501'
down_revision = 'a210b943ec82'
branch_labels = None
depends_on = None


def upgrade():
    table = sa.table('publication_interest', sa.column('slug', sa.String), sa.column('votes', sa.Integer))
    op.bulk_insert(table, [{'slug': 'orden-na-sdachu', 'votes': 0}])


def downgrade():
    votes = sa.table('publication_vote', sa.column('book_slug', sa.String))
    totals = sa.table('publication_interest', sa.column('slug', sa.String))
    op.execute(votes.delete().where(votes.c.book_slug == 'orden-na-sdachu'))
    op.execute(totals.delete().where(totals.c.slug == 'orden-na-sdachu'))
