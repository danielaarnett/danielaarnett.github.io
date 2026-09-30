"""Use the six author-selected shelves, preserving existing works."""
from alembic import op
import sqlalchemy as sa

revision = 'e3a142b09c65'
down_revision = 'c19f4d8a2031'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('work') as batch:
        batch.drop_constraint('work_shelf', type_='check')
        batch.alter_column('shelf', existing_type=sa.String(16), server_default='unfinished', existing_nullable=False)
    op.execute(sa.text("UPDATE work SET shelf='unfinished' WHERE shelf='stories'"))
    with op.batch_alter_table('work') as batch:
        batch.create_check_constraint('work_shelf', "shelf IN ('novellas','short_novels','novels','scripts','unfinished','poetry')")


def downgrade():
    with op.batch_alter_table('work') as batch:
        batch.drop_constraint('work_shelf', type_='check')
        batch.alter_column('shelf', existing_type=sa.String(16), server_default='stories', existing_nullable=False)
    op.execute(sa.text("UPDATE work SET shelf='stories' WHERE shelf IN ('short_novels','scripts','unfinished')"))
    with op.batch_alter_table('work') as batch:
        batch.create_check_constraint('work_shelf', "shelf IN ('novels','novellas','poetry','stories')")
