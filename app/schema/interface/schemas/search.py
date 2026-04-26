"""Schema Search DTOs"""

from pydantic import BaseModel, ConfigDict, Field

# Python 3.12 Type Alias
type TotalCount = int


class SchemaSearchItem(BaseModel):
    """검색 결과 항목 (유연한 검증)"""

    model_config = ConfigDict(
        extra="ignore",
        frozen=True,
    )

    subject: str = Field(..., description="Subject 이름")
    version: int = Field(..., description="버전")
    storage_url: str | None = Field(None, description="저장소 URL")
    checksum: str | None = Field(None, description="해시")
    owner: str | None = Field(None, description="소유자")
    compatibility_mode: str | None = Field(None, description="호환성 모드")
    schema_type: str | None = Field(None, description="스키마 타입")
    created_at: str | None = Field(None, description="생성 시간")


class SchemaSearchResponse(BaseModel):
    """스키마 검색 응답"""

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "subject": "order.payment",
                        "version": 5,
                        "storage_url": "s3://bucket/schemas/order.payment.avsc",
                        "checksum": "a1b2c3d4",
                        "compatibility_mode": "FULL_TRANSITIVE",
                        "owner": "payment-team",
                    }
                ],
                "total": 150,
                "page": 1,
                "limit": 20,
            }
        },
    )

    items: list[SchemaSearchItem] = Field(..., description="검색된 스키마 목록")
    total: TotalCount = Field(..., description="전체 검색 결과 수")
    page: int = Field(..., description="현재 페이지 번호")
    limit: int = Field(..., description="페이지 당 항목 수")
