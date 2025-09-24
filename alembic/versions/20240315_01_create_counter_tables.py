"""Create counter tables"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20240315_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "counter_ledger",
        sa.Column("national_id", sa.String(length=10), nullable=False),
        sa.Column("counter", sa.String(length=9), nullable=False),
        sa.Column("year_code", sa.String(length=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("national_id"),
        sa.UniqueConstraint("counter"),
        sa.CheckConstraint(
            "length(national_id) = 10 AND national_id >= '0000000000' AND national_id <= '9999999999'",
            name="ck_counter_ledger_national_id",
        ),
        sa.CheckConstraint(
            "length(counter) = 9 AND substr(counter,3,3) IN ('357','373')",
            name="ck_counter_format_prefix",
        ),
        sa.CheckConstraint("counter >= '000000000' AND counter <= '999999999'", name="ck_counter_digits"),
    )

    op.create_table(
        "counter_sequences",
        sa.Column("year_code", sa.String(length=2), nullable=False),
        sa.Column("prefix", sa.String(length=3), nullable=False),
        sa.Column("next_seq", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("year_code", "prefix", name="pk_counter_sequences"),
        sa.CheckConstraint("prefix IN ('357','373')", name="ck_counter_sequences_prefix"),
        sa.CheckConstraint("next_seq BETWEEN 1 AND 10000", name="ck_counter_sequences_bounds"),
    )


def downgrade() -> None:
    op.drop_table("counter_sequences")
    op.drop_table("counter_ledger")
