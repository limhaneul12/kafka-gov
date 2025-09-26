"""Schema MySQL Repository 구현체"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schema.domain.models import (
    ChangeId,
    Environment,
    SchemaApplyResult,
    SchemaArtifact,
    SchemaPlan,
    SchemaPlanItem,
)
from app.schema.domain.repositories.interfaces import ISchemaMetadataRepository
from app.schema.infrastructure.models import (
    SchemaApplyResultModel,
    SchemaArtifactModel,
    SchemaPlanModel,
)

logger = logging.getLogger(__name__)


class MySQLSchemaMetadataRepository(ISchemaMetadataRepository):
    """MySQL 기반 스키마 메타데이터 리포지토리"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save_plan(self, plan: SchemaPlan, created_by: str) -> None:
        """계획 저장"""
        try:
            # SchemaPlan 도메인 객체를 JSON으로 직렬화
            plan_data = {
                "change_id": plan.change_id,
                "env": plan.env.value,
                "items": [
                    {
                        "subject": item.subject,
                        "action": item.action.value,
                        "current_version": item.current_version,
                        "target_version": item.target_version,
                        "diff": item.diff,
                    }
                    for item in plan.items
                ],
                "violations": [
                    {
                        "subject": v.subject,
                        "rule": v.rule,
                        "message": v.message,
                        "severity": v.severity,
                        "field": v.field,
                    }
                    for v in plan.violations
                ],
                "compatibility_reports": [
                    {
                        "subject": report.subject,
                        "mode": report.mode.value if hasattr(report.mode, "value") else report.mode,
                        "is_compatible": report.is_compatible,
                        "issues": [
                            {
                                "path": issue.path,
                                "message": issue.message,
                                "issue_type": issue.issue_type,
                            }
                            for issue in report.issues
                        ],
                    }
                    for report in plan.compatibility_reports
                ],
                "impacts": [
                    {
                        "subject": impact.subject,
                        "topics": list(impact.topics),
                        "consumers": list(impact.consumers),
                    }
                    for impact in plan.impacts
                ],
            }

            plan_model = SchemaPlanModel(
                change_id=plan.change_id,
                env=plan.env.value,
                plan_data=plan_data,
                can_apply=plan.can_apply,
                created_by=created_by,
            )

            self.session.add(plan_model)
            await self.session.flush()

            logger.info(f"Schema plan saved: {plan.change_id}")

        except Exception as e:
            logger.error(f"Failed to save schema plan {plan.change_id}: {e}")
            raise

    async def get_plan(self, change_id: ChangeId) -> SchemaPlan | None:
        """계획 조회"""
        try:
            stmt = select(SchemaPlanModel).where(SchemaPlanModel.change_id == change_id)
            result = await self.session.execute(stmt)
            plan_model = result.scalar_one_or_none()

            if plan_model is None:
                return None

            # JSON 데이터를 SchemaPlan 도메인 객체로 역직렬화
            plan_data = plan_model.plan_data

            # 계획 아이템 역직렬화
            from app.schema.domain.models import PlanAction

            items = [
                SchemaPlanItem(
                    subject=item["subject"],
                    action=PlanAction(item["action"]),
                    current_version=item["current_version"],
                    target_version=item["target_version"],
                    diff=item["diff"],
                )
                for item in plan_data["items"]
            ]

            # 정책 위반 역직렬화
            from app.schema.domain.models import PolicyViolation

            violations = [
                PolicyViolation(
                    subject=v["subject"],
                    rule=v["rule"],
                    message=v["message"],
                    severity=v["severity"],
                    field=v["field"],
                )
                for v in plan_data["violations"]
            ]

            # 호환성 보고서 역직렬화
            from app.schema.domain.models import (
                CompatibilityMode,
                SchemaCompatibilityIssue,
                SchemaCompatibilityReport,
            )

            compatibility_reports = [
                SchemaCompatibilityReport(
                    subject=report["subject"],
                    mode=CompatibilityMode(report["mode"]),
                    is_compatible=report["is_compatible"],
                    issues=tuple(
                        SchemaCompatibilityIssue(
                            path=issue["path"],
                            message=issue["message"],
                            issue_type=issue["issue_type"],
                        )
                        for issue in report["issues"]
                    ),
                )
                for report in plan_data.get("compatibility_reports", [])
            ]

            # 영향도 정보 역직렬화
            from app.schema.domain.models import SchemaImpactRecord

            impacts = [
                SchemaImpactRecord(
                    subject=impact["subject"],
                    topics=tuple(impact["topics"]),
                    consumers=tuple(impact["consumers"]),
                )
                for impact in plan_data.get("impacts", [])
            ]

            # Environment enum으로 변환
            env = Environment(plan_data["env"])

            return SchemaPlan(
                change_id=plan_data["change_id"],
                env=env,
                items=tuple(items),
                violations=tuple(violations),
                compatibility_reports=tuple(compatibility_reports),
                impacts=tuple(impacts),
            )

        except Exception as e:
            logger.error(f"Failed to get schema plan {change_id}: {e}")
            raise

    async def save_apply_result(self, result: SchemaApplyResult, applied_by: str) -> None:
        """적용 결과 저장"""
        try:
            # SchemaApplyResult 도메인 객체를 JSON으로 직렬화
            result_data = {
                "change_id": result.change_id,
                "env": result.env.value,
                "registered": list(result.registered),
                "skipped": list(result.skipped),
                "failed": [
                    {
                        "subject": failed_item.get("subject", "unknown"),
                        "error": failed_item.get("error", "unknown error"),
                    }
                    for failed_item in result.failed
                ],
                "audit_id": result.audit_id,
                "artifacts": [
                    {
                        "subject": artifact.subject,
                        "version": artifact.version,
                        "storage_url": artifact.storage_url,
                        "checksum": artifact.checksum,
                    }
                    for artifact in result.artifacts
                ],
                "summary": result.summary(),
            }

            registered_count = len(result.registered)
            failed_count = len(result.failed)

            result_model = SchemaApplyResultModel(
                change_id=result.change_id,
                result_data=result_data,
                registered_count=registered_count,
                failed_count=failed_count,
                applied_by=applied_by,
            )

            self.session.add(result_model)
            await self.session.flush()

            logger.info(f"Schema apply result saved: {result.change_id}")

        except Exception as e:
            logger.error(f"Failed to save schema apply result {result.change_id}: {e}")
            raise

    async def record_artifact(self, artifact: SchemaArtifact, change_id: ChangeId) -> None:
        """아티팩트 기록"""
        try:
            artifact_model = SchemaArtifactModel(
                subject=artifact.subject,
                version=artifact.version,
                storage_url=artifact.storage_url,
                checksum=artifact.checksum,
                change_id=change_id,
                schema_type="UNKNOWN",  # 실제 구현에서는 artifact에서 가져와야 함
            )

            self.session.add(artifact_model)
            await self.session.flush()

            logger.info(f"Schema artifact recorded: {artifact.subject} v{artifact.version}")

        except Exception as e:
            logger.error(f"Failed to record schema artifact {artifact.subject}: {e}")
            raise

    async def save_upload_result(self, upload: Any, uploaded_by: str) -> None:
        """업로드 결과 저장 (미구현)"""
        # TODO: SchemaUploadResult 모델 구현 후 추가
        raise NotImplementedError("Schema upload result saving not implemented yet")
