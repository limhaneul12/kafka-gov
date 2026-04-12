from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "6f5f0c8f6c1f"
down_revision: str | Sequence[str] | None = "a6f4f39b9c12"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index(
        op.f("ix_topic_partition_metrics_topic_name"), table_name="topic_partition_metrics"
    )
    op.drop_index(
        op.f("ix_topic_partition_metrics_snapshot_id"), table_name="topic_partition_metrics"
    )
    op.drop_index("idx_topic_name", table_name="topic_partition_metrics")
    op.drop_index("idx_snapshot_topic", table_name="topic_partition_metrics")
    op.drop_table("topic_partition_metrics")

    op.drop_index(op.f("ix_leader_distributions_snapshot_id"), table_name="leader_distributions")
    op.drop_index("idx_snapshot_broker", table_name="leader_distributions")
    op.drop_table("leader_distributions")

    op.drop_index(op.f("ix_metrics_snapshots_collected_at"), table_name="metrics_snapshots")
    op.drop_index(op.f("ix_metrics_snapshots_cluster_id"), table_name="metrics_snapshots")
    op.drop_index("idx_cluster_collected", table_name="metrics_snapshots")
    op.drop_table("metrics_snapshots")

    op.drop_table("topic_apply_results")
    op.drop_table("topic_plans")
    op.drop_table("topic_metadata")
    op.drop_table("policies")
    op.drop_table("audit_logs")


def downgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="로그 ID"),
        sa.Column("change_id", sa.String(length=100), nullable=False, comment="변경 ID"),
        sa.Column("action", sa.String(length=50), nullable=False, comment="액션"),
        sa.Column("target", sa.String(length=255), nullable=False, comment="대상 (토픽명)"),
        sa.Column("team", sa.String(length=100), nullable=True, comment="팀 (토픽 소유자)"),
        sa.Column("actor", sa.String(length=100), nullable=False, comment="수행자"),
        sa.Column("status", sa.String(length=20), nullable=False, comment="상태"),
        sa.Column("message", sa.Text(), nullable=True, comment="메시지"),
        sa.Column("snapshot", sa.JSON(), nullable=True, comment="스냅샷 (JSON)"),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="로그 시간",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
    )

    op.create_table(
        "policies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="레코드 ID"),
        sa.Column("policy_id", sa.String(length=36), nullable=False, comment="정책 UUID"),
        sa.Column("version", sa.Integer(), nullable=False, comment="버전 번호 (1, 2, 3...)"),
        sa.Column(
            "policy_type",
            sa.Enum("naming", "guardrail", name="policy_type_enum"),
            nullable=False,
            comment="정책 타입",
        ),
        sa.Column("name", sa.String(length=255), nullable=False, comment="정책 이름"),
        sa.Column("description", sa.Text(), nullable=False, comment="정책 설명"),
        sa.Column(
            "status",
            sa.Enum("draft", "active", "archived", name="policy_status_enum"),
            nullable=False,
            comment="정책 상태",
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
            server_default=sa.text("CURRENT_TIMESTAMP"),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_policies")),
        sa.UniqueConstraint("policy_id", "version", name="uq_policy_version"),
        comment="정책 버전 관리 테이블",
    )

    op.create_table(
        "topic_metadata",
        sa.Column("topic_name", sa.String(length=255), nullable=False, comment="토픽 이름"),
        sa.Column("owners", sa.JSON(), nullable=True, comment="소유자 목록 (JSON 배열)"),
        sa.Column("doc", sa.Text(), nullable=True, comment="문서/설명"),
        sa.Column("tags", sa.JSON(), nullable=True, comment="태그 (JSON)"),
        sa.Column(
            "environment", sa.String(length=20), nullable=True, comment="환경 (dev/stg/prod)"
        ),
        sa.Column("slo", sa.Text(), nullable=True, comment="SLO (Service Level Objective)"),
        sa.Column("sla", sa.Text(), nullable=True, comment="SLA (Service Level Agreement)"),
        sa.Column("config", sa.JSON(), nullable=True, comment="토픽 설정"),
        sa.Column("created_by", sa.String(length=100), nullable=False, comment="생성자"),
        sa.Column("updated_by", sa.String(length=100), nullable=False, comment="수정자"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="생성 시간",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="수정 시간",
        ),
        sa.PrimaryKeyConstraint("topic_name", name=op.f("pk_topic_metadata")),
    )

    op.create_table(
        "topic_plans",
        sa.Column("change_id", sa.String(length=100), nullable=False, comment="변경 ID"),
        sa.Column("env", sa.String(length=50), nullable=False, comment="환경 (dev/staging/prod)"),
        sa.Column("plan_data", sa.JSON(), nullable=False, comment="계획 데이터 (JSON)"),
        sa.Column("status", sa.String(length=20), nullable=False, comment="상태"),
        sa.Column("can_apply", sa.Boolean(), nullable=False, comment="적용 가능 여부"),
        sa.Column("created_by", sa.String(length=100), nullable=False, comment="생성자"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="생성 시간",
        ),
        sa.Column("updated_by", sa.String(length=100), nullable=True, comment="수정자"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, comment="수정 시간"),
        sa.PrimaryKeyConstraint("change_id", name=op.f("pk_topic_plans")),
    )

    op.create_table(
        "topic_apply_results",
        sa.Column("change_id", sa.String(length=100), nullable=False, comment="변경 ID"),
        sa.Column("result_data", sa.JSON(), nullable=False, comment="적용 결과 (JSON)"),
        sa.Column("success_count", sa.Integer(), nullable=False, comment="성공 개수"),
        sa.Column("failure_count", sa.Integer(), nullable=False, comment="실패 개수"),
        sa.Column("applied_by", sa.String(length=100), nullable=False, comment="적용자"),
        sa.Column(
            "applied_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="적용 시간",
        ),
        sa.PrimaryKeyConstraint("change_id", name=op.f("pk_topic_apply_results")),
    )

    op.create_table(
        "metrics_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cluster_id", sa.String(length=100), nullable=False),
        sa.Column("collected_at", sa.DateTime(), nullable=False),
        sa.Column("broker_count", sa.Integer(), nullable=False),
        sa.Column("total_partitions", sa.Integer(), nullable=False),
        sa.Column("partition_to_broker_ratio", sa.Float(), nullable=False),
        sa.Column("log_dir", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_metrics_snapshots")),
    )
    op.create_index(
        "idx_cluster_collected",
        "metrics_snapshots",
        ["cluster_id", "collected_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_metrics_snapshots_cluster_id"),
        "metrics_snapshots",
        ["cluster_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_metrics_snapshots_collected_at"),
        "metrics_snapshots",
        ["collected_at"],
        unique=False,
    )

    op.create_table(
        "leader_distributions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("snapshot_id", sa.Integer(), nullable=False),
        sa.Column("broker_id", sa.Integer(), nullable=False),
        sa.Column("leader_partition_count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["metrics_snapshots.id"],
            name=op.f("fk_leader_distributions_snapshot_id_metrics_snapshots"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_leader_distributions")),
    )
    op.create_index(
        "idx_snapshot_broker",
        "leader_distributions",
        ["snapshot_id", "broker_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_leader_distributions_snapshot_id"),
        "leader_distributions",
        ["snapshot_id"],
        unique=False,
    )

    op.create_table(
        "topic_partition_metrics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("snapshot_id", sa.Integer(), nullable=False),
        sa.Column("topic_name", sa.String(length=255), nullable=False),
        sa.Column("partition_count", sa.Integer(), nullable=False),
        sa.Column("total_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("avg_partition_size", sa.BigInteger(), nullable=False),
        sa.Column("max_partition_size", sa.BigInteger(), nullable=False),
        sa.Column("min_partition_size", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["metrics_snapshots.id"],
            name=op.f("fk_topic_partition_metrics_snapshot_id_metrics_snapshots"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_topic_partition_metrics")),
    )
    op.create_index(
        "idx_snapshot_topic",
        "topic_partition_metrics",
        ["snapshot_id", "topic_name"],
        unique=False,
    )
    op.create_index("idx_topic_name", "topic_partition_metrics", ["topic_name"], unique=False)
    op.create_index(
        op.f("ix_topic_partition_metrics_snapshot_id"),
        "topic_partition_metrics",
        ["snapshot_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_topic_partition_metrics_topic_name"),
        "topic_partition_metrics",
        ["topic_name"],
        unique=False,
    )
