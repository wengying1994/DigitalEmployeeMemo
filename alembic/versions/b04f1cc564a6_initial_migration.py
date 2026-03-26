"""initial migration

Revision ID: b04f1cc564a6
Revises:
Create Date: 2026-03-26 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b04f1cc564a6'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create departments table
    op.create_table('departments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('leader_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_departments_leader_id', 'departments', ['leader_id'], unique=False)
    op.create_index('ix_departments_name', 'departments', ['name'], unique=True)

    # Create users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('dept_id', sa.Integer(), nullable=True),
        sa.Column('role', sa.String(length=20), server_default='member', nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['dept_id'], ['departments.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_dept_id', 'users', ['dept_id'], unique=False)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # Create messages table
    op.create_table('messages',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('sender_id', sa.Integer(), nullable=False),
        sa.Column('receiver_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_read', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['receiver_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_messages_receiver_id', 'messages', ['receiver_id'], unique=False)
    op.create_index('ix_messages_sender_id', 'messages', ['sender_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_messages_sender_id', table_name='messages')
    op.drop_index('ix_messages_receiver_id', table_name='messages')
    op.drop_table('messages')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_index('ix_users_dept_id', table_name='users')
    op.drop_table('users')
    op.drop_index('ix_departments_name', table_name='departments')
    op.drop_index('ix_departments_leader_id', table_name='departments')
    op.drop_table('departments')
