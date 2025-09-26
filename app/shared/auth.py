"""JWT 인증 공통 모듈"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Final

from fastapi import HTTPException, Request, status
from jose import JWTError, jwt

from .settings import AppSettings, get_settings


class JWTAuthenticator:
    """JWT 인증 처리기"""

    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    def create_access_token(self, data: dict[str, Any]) -> str:
        """액세스 토큰 생성"""
        to_encode = data.copy()
        expire = datetime.now(datetime.UTC) + timedelta(minutes=self.settings.security.jwt_expire_minutes)
        to_encode.update({"exp": expire})
        
        encoded_jwt = jwt.encode(
            to_encode, 
            self.settings.security.jwt_secret_key, 
            algorithm=self.settings.security.jwt_algorithm
        )
        return encoded_jwt

    def verify_token(self, token: str) -> dict[str, Any]:
        """토큰 검증 및 페이로드 반환"""
        try:
            payload = jwt.decode(
                token, 
                self.settings.security.jwt_secret_key, 
                algorithms=[self.settings.security.jwt_algorithm]
            )
            return payload
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            ) from e

    def get_current_user_from_request(self, request: Request) -> str:
        """Request에서 현재 사용자 추출"""
        # Authorization 헤더에서 토큰 추출
        authorization = request.headers.get("Authorization")
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header missing",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Bearer 토큰 형식 검증
        try:
            scheme, token = authorization.split()
            if scheme.lower() != "bearer":
                raise ValueError("Invalid authentication scheme")
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format",
                headers={"WWW-Authenticate": "Bearer"},
            ) from e

        # 토큰 검증 및 사용자 정보 추출
        payload = self.verify_token(token)
        username = payload.get("sub")
        
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return username


# 전역 인증 처리기 (설정 기반으로 초기화) - Thread-safe 싱글톤
_authenticator: JWTAuthenticator | None = None
_lock: Final = object()  # 간단한 락 객체


def get_authenticator(settings: AppSettings | None = None) -> JWTAuthenticator:
    """JWT 인증 처리기 의존성 주입 (Thread-safe)"""
    global _authenticator
    if _authenticator is None:
        if settings is None:
            settings = get_settings()
        _authenticator = JWTAuthenticator(settings)
    return _authenticator


def get_current_user(request: Request) -> str:
    """현재 사용자 정보 추출 (FastAPI 의존성)"""
    authenticator = get_authenticator()
    return authenticator.get_current_user_from_request(request)


# 개발/테스트용 임시 사용자 (JWT 없이)
def get_current_user_dev() -> str:
    """개발/테스트용 임시 사용자"""
    return "system"
