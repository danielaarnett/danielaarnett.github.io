"""Add library shelves and expiring, server-assigned reader tiers."""
from alembic import op
import sqlalchemy as sa

revision = 'c19f4d8a2031'
down_revision = '7ade4fc77f8f'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user') as batch:
        batch.add_column(sa.Column('subscription_tier', sa.String(16), server_default='free', nullable=False))
        batch.add_column(sa.Column('subscription_expires_at', sa.DateTime(), nullable=True))
        batch.create_check_constraint('user_subscription_tier', "subscription_tier IN ('free','witness','appreciator')")
    with op.batch_alter_table('work') as batch:
        batch.add_column(sa.Column('shelf', sa.String(16), server_default='stories', nullable=False))
        batch.add_column(sa.Column('minimum_tier', sa.String(16), server_default='free', nullable=False))
        batch.create_check_constraint('work_shelf', "shelf IN ('novels','novellas','poetry','stories')")
        batch.create_check_constraint('work_minimum_tier', "minimum_tier IN ('free','witness','appreciator')")
    op.execute(sa.text("UPDATE work SET shelf='novels' WHERE subtitle='Роман'"))
    op.execute(sa.text("UPDATE work SET shelf='novellas' WHERE slug='iam-sero-est'"))
    op.execute(sa.text("UPDATE work SET minimum_tier='witness' WHERE access_type='subscriber'"))


def downgrade():
    with op.batch_alter_table('work') as batch:
        batch.drop_constraint('work_shelf', type_='check')
        batch.drop_constraint('work_minimum_tier', type_='check')
        batch.drop_column('shelf')
        batch.drop_column('minimum_tier')
    with op.batch_alter_table('user') as batch:
        batch.drop_constraint('user_subscription_tier', type_='check')
        batch.drop_column('subscription_tier')
        batch.drop_column('subscription_expires_at')
