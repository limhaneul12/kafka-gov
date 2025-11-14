"""애플리케이션 설정 - DB 기반 동적 구성"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def model_config_module(env_prefix: str) -> SettingsConfigDict:
    return SettingsConfigDict(
        env_prefix=env_prefix,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class DatabaseSettings(BaseSettings):
    """데이터베이스 설정 (유일한 정적 설정)"""

    model_config = model_config_module("DB_")

    # MySQL 연결 설정
    host: str = Field(default="mysql", description="데이터베이스 호스트")
    port: int = Field(default=3306, ge=1, le=65535, description="데이터베이스 포트")
    username: str = Field(default="user", description="데이터베이스 사용자명")
    password: str = Field(default="password", description="데이터베이스 비밀번호")
    database: str = Field(default="kafka_gov", description="데이터베이스명")

    # 연결 풀 설정
    pool_size: int = Field(default=10, ge=1, le=100, description="연결 풀 크기")
    max_overflow: int = Field(default=20, ge=0, le=100, description="최대 오버플로우")
    pool_recycle: int = Field(default=3600, ge=300, description="연결 재사용 시간(초)")

    # 기타 설정
    echo: bool = Field(default=False, description="SQL 쿼리 로깅")

    @property
    def url(self) -> str:
        """데이터베이스 연결 URL 생성"""
        return f"mysql+aiomysql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"


class AppSettings(BaseSettings):
    """애플리케이션 설정 (최소화)"""

    model_config = model_config_module("APP_")

    # 애플리케이션 기본 설정
    app_name: str = Field(default="Kafka Governance", description="애플리케이션 이름")
    app_version: str = Field(default="1.0.0", description="애플리케이션 버전")
    debug: bool = Field(default=False, description="디버그 모드")
    environment: str = Field(
        default="development", description="실행 환경 (development/staging/production)"
    )

    # CORS 설정
    cors_origins: str | list[str] = Field(
        default="*",
        description="허용할 CORS 오리진 목록 (콤마로 구분 또는 JSON 배열)",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """CORS origins를 환경 변수에서 파싱

        - 문자열인 경우: 콤마로 분리
        - 이미 리스트인 경우: 그대로 반환
        """
        if isinstance(v, str):
            # 빈 문자열이면 기본값
            if not v or v.strip() == "":
                return ["*"]
            # 콤마로 구분된 문자열 파싱
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # 데이터베이스 설정 (유일한 하위 설정)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)

    @property
    def is_production(self) -> bool:
        """프로덕션 환경 여부"""
        return self.environment.lower() in ("prod", "production")

    @property
    def is_development(self) -> bool:
        """개발 환경 여부"""
        return self.environment.lower() in ("dev", "development", "local")

    @property
    def parsed_cors_origins(self) -> list[str]:
        """CORS origins 반환 (validator에서 이미 파싱됨)"""
        # validator에서 이미 list[str]로 변환되었으므로 그대로 반환
        if isinstance(self.cors_origins, list):
            return self.cors_origins
        # 혹시 모를 경우 대비
        return [self.cors_origins] if self.cors_origins else ["*"]


@lru_cache
def get_settings() -> AppSettings:
    """설정 인스턴스 반환 (캐시됨)"""
    return AppSettings()


# 전역 설정 인스턴스
settings = get_settings()
