"""add workid

Revision ID: 4f3c7353c17b
Revises: 9f98dad18a3b
Create Date: 2021-03-11 02:33:55.206481

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4f3c7353c17b'
down_revision = '9f98dad18a3b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('workid', sa.String(length=64), nullable=True))
    op.drop_index('ix_users_username', table_name='users')
    op.create_index(op.f('ix_users_name'), 'users', ['name'], unique=True)
    op.create_index(op.f('ix_users_workid'), 'users', ['workid'], unique=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_users_workid'), table_name='users')
    op.drop_index(op.f('ix_users_name'), table_name='users')
    op.create_index('ix_users_username', 'users', ['username'], unique=1)
    op.drop_column('users', 'workid')
    # ### end Alembic commands ###
