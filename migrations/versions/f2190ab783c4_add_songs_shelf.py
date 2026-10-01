"""Add the songs shelf."""
from alembic import op
import sqlalchemy as sa

revision = 'f2190ab783c4'
down_revision = 'e3a142b09c65'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('work') as batch:
        batch.drop_constraint('work_shelf', type_='check')
        batch.create_check_constraint('work_shelf', "shelf IN ('novellas','short_novels','novels','scripts','unfinished','poetry','songs')")


def downgrade():
    op.execute(sa.text("UPDATE work SET shelf='poetry' WHERE shelf='songs'"))
    with op.batch_alter_table('work') as batch:
        batch.drop_constraint('work_shelf', type_='check')
        batch.create_check_constraint('work_shelf', "shelf IN ('novellas','short_novels','novels','scripts','unfinished','poetry')")
