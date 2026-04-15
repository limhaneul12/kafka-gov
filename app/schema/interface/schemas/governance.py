"""Schema Governance DTOs."""

from pydantic import BaseModel, ConfigDict, Field

from app.schema.interface.types.enums import CompatibilityMode

type Score = float


class GovernanceScore(BaseModel):
    model_config = ConfigDict(frozen=True)

    compatibility_pass_rate: Score = Field(..., description="호환성 검사 통과율 (0.0~1.0)")
    documentation_coverage: Score = Field(..., description="문서(doc) 작성 비율 (0.0~1.0)")
    average_lint_score: Score = Field(..., description="평균 린트 점수 (0.0~1.0)")
    total_score: Score = Field(..., description="종합 점수 (0.0~1.0)")


class SubjectStat(BaseModel):
    model_config = ConfigDict(frozen=True)

    subject: str = Field(..., description="Subject 이름")
    owner: str | None = Field(None, description="소유 팀/담당자")
    version_count: int = Field(..., description="전체 버전 수", ge=0)
    last_updated: str = Field(..., description="최근 업데이트 시간 (ISO8601)")
    compatibility_mode: CompatibilityMode | None = Field(None, description="설정된 호환성 모드")
    lint_score: Score = Field(..., description="린트 품질 점수")
    has_doc: bool = Field(..., description="문서(doc) 메타데이터 존재 여부")


class DashboardResponse(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={
            "example": {
                "total_subjects": 150,
                "total_versions": 840,
                "orphan_subjects": 12,
                "scores": {
                    "compatibility_pass_rate": 0.98,
                    "documentation_coverage": 0.45,
                    "average_lint_score": 0.82,
                    "total_score": 0.75,
                },
                "top_subjects": [
                    {
                        "subject": "order.payment.v1",
                        "owner": "payment-team",
                        "version_count": 5,
                        "last_updated": "2024-03-20T10:00:00Z",
                        "compatibility_mode": "BACKWARD",
                        "lint_score": 0.95,
                        "has_doc": True,
                    }
                ],
            }
        },
    )

    total_subjects: int = Field(..., description="전체 Subject 수")
    total_versions: int = Field(..., description="전체 스키마 버전 수 합계")
    orphan_subjects: int = Field(..., description="Owner가 없는 고아 Subject 수")
    scores: GovernanceScore = Field(..., description="거버넌스 종합 점수")
    top_subjects: list[SubjectStat] = Field(..., description="주요 Subject 목록")


class SchemaHistoryItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: int = Field(..., description="스키마 버전")
    schema_id: int = Field(..., description="Schema ID")
    created_at: str | None = Field(None, description="생성 시간 (SR 미지원 시 null)")
    diff_type: str = Field(..., description="변경 유형 (CREATE, UPDATE 등)")
    author: str | None = Field(None, description="작성자 (메타데이터)")
    commit_message: str | None = Field(None, description="변경 사유 (메타데이터)")


class SchemaHistoryResponse(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={
            "example": {
                "subject": "order.payment",
                "history": [
                    {
                        "version": 2,
                        "schema_id": 105,
                        "diff_type": "UPDATE",
                        "author": "jane.doe",
                        "commit_message": "Add refund_reason field",
                    },
                    {
                        "version": 1,
                        "schema_id": 98,
                        "diff_type": "CREATE",
                        "author": "john.doe",
                        "commit_message": "Initial schema",
                    },
                ],
            }
        },
    )

    subject: str = Field(..., description="Subject 이름")
    history: list[SchemaHistoryItem] = Field(..., description="변경 이력 목록 (최신순)")
