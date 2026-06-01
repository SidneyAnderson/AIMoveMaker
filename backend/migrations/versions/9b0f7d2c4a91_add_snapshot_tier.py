"""Add tier column to snapshots.

Revision ID: 9b0f7d2c4a91
Revises: 3857d22c304f
Create Date: 2026-05-31 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9b0f7d2c4a91"
down_revision: Union[str, None] = "3857d22c304f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SNAPSHOT_TIERS = ("auto", "manual", "major", "handoff")


def _tier_column_type(dialect_name: str):
    if dialect_name == "postgresql":
        return sa.Enum(*SNAPSHOT_TIERS, name="snapshot_tier_enum")
    return sa.String(length=20)


def upgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    if dialect_name == "postgresql":
        sa.Enum(*SNAPSHOT_TIERS, name="snapshot_tier_enum").create(bind, checkfirst=True)

    with op.batch_alter_table("snapshots") as batch_op:
        batch_op.add_column(
            sa.Column(
                "tier",
                _tier_column_type(dialect_name),
                nullable=False,
                server_default="manual",
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    with op.batch_alter_table("snapshots") as batch_op:
        batch_op.drop_column("tier")

    if dialect_name == "postgresql":
        sa.Enum(*SNAPSHOT_TIERS, name="snapshot_tier_enum").drop(bind, checkfirst=True)
