"""roles table: users.role becomes a checked reference

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-21 14:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

ROLES = [
    {"name": "user", "description": "Can analyse content and manage their own account and history."},
    {"name": "admin", "description": "Can also manage accounts, review feedback, read the audit log and see model status."},
]


def upgrade() -> None:
    roles = op.create_table(
        "roles",
        sa.Column("name", sa.String(length=20), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("name"),
    )
    op.bulk_insert(roles, ROLES)
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.create_foreign_key("fk_users_role_roles", "roles", ["role"], ["name"])


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_constraint("fk_users_role_roles", type_="foreignkey")
    op.drop_table("roles")
