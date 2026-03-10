from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a6f4f39b9c12"
down_revision: Union[str, Sequence[str], None] = "feeb4168b5fc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "approval_requests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("request_id", sa.String(length=36), nullable=False, comment="승인 요청 UUID"),
        sa.Column("resource_type", sa.String(length=32), nullable=False, comment="리소스 타입"),
        sa.Column("resource_name", sa.String(length=255), nullable=False, comment="리소스 이름"),
        sa.Column("change_type", sa.String(length=64), nullable=False, comment="변경 유형"),
        sa.Column(
            "change_ref", sa.String(length=100), nullable=True, comment="change_id 등 외부 참조"
        ),
        sa.Column("summary", sa.Text(), nullable=False, comment="요청 요약"),
        sa.Column("justification", sa.Text(), nullable=False, comment="요청 사유"),
        sa.Column("requested_by", sa.String(length=100), nullable=False, comment="요청자"),
        sa.Column("status", sa.String(length=20), nullable=False, comment="상태"),
        sa.Column("approver", sa.String(length=100), nullable=True, comment="승인/반려자"),
        sa.Column("decision_reason", sa.Text(), nullable=True, comment="승인/반려 사유"),
        sa.Column("metadata", sa.JSON(), nullable=True, comment="추가 메타데이터"),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
            comment="요청 시간",
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True, comment="결정 시간"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_approval_requests")),
        sa.UniqueConstraint("request_id", name="uq_approval_request_request_id"),
        comment="승인 요청 상태 저장 테이블",
    )
    op.create_index(
        "idx_approval_requests_status_requested_at",
        "approval_requests",
        ["status", "requested_at"],
        unique=False,
    )
    op.create_index(
        "idx_approval_requests_resource_type",
        "approval_requests",
        ["resource_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_approval_requests_resource_type", table_name="approval_requests")
    op.drop_index("idx_approval_requests_status_requested_at", table_name="approval_requests")
    op.drop_table("approval_requests")
