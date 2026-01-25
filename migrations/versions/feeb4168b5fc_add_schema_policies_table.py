"""add schema_policies table

Revision ID: feeb4168b5fc
Revises: df9847a07952
Create Date: 2026-01-25 13:45:15.331395

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "feeb4168b5fc"
down_revision: Union[str, Sequence[str], None] = "df9847a07952"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "schema_policies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="레코드 ID"),
        sa.Column("policy_id", sa.String(length=36), nullable=False, comment="정책 UUID"),
        sa.Column("version", sa.Integer(), nullable=False, comment="버전 번호 (1, 2, 3...)"),
        sa.Column(
            "policy_type",
            sa.String(length=20),
            nullable=False,
            comment="정책 타입 (lint/guardrail)",
        ),
        sa.Column("name", sa.String(length=255), nullable=False, comment="정책 이름"),
        sa.Column("description", sa.Text(), nullable=False, comment="정책 설명"),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            comment="정책 상태 (draft/active/archived)",
        ),
        sa.Column("content", sa.JSON(), nullable=False, comment="정책 내용 (JSON)"),
        sa.Column(
            "target_environment",
            sa.String(length=20),
            server_default="total",
            nullable=False,
            comment="적용 환경",
        ),
        sa.Column("created_by", sa.String(length=255), nullable=False, comment="생성자"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
            comment="생성 시간",
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, comment="수정 시간"),
        sa.Column(
            "activated_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="활성화 시간 (ACTIVE 상태가 된 시점)",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_schema_policies")),
        sa.UniqueConstraint("policy_id", "version", name="uq_schema_policy_version"),
        comment="스키마 정책 버전 관리 테이블",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("schema_policies")
