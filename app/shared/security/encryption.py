"""암호화/복호화 유틸리티

Fernet (대칭키 암호화)를 사용하여 민감 정보를 안전하게 저장
"""

from __future__ import annotations

import base64
import os

from cryptography.fernet import Fernet


class EncryptionService:
    """암호화/복호화 서비스

    환경변수 ENCRYPTION_KEY를 사용하여 암호화/복호화 수행
    키가 없으면 자동 생성 (개발 환경 전용)
    """

    def __init__(self, encryption_key: str | None = None) -> None:
        """
        Args:
            encryption_key: Base64로 인코딩된 32바이트 키
                           None이면 환경변수 ENCRYPTION_KEY 사용
        """
        key = encryption_key or os.getenv("ENCRYPTION_KEY")

        if not key:
            # 개발 환경: 키 자동 생성 (프로덕션에서는 반드시 환경변수 설정 필요)
            key = Fernet.generate_key().decode()
            print(f"⚠️  WARNING: Using auto-generated encryption key: {key}")
            print("⚠️  Set ENCRYPTION_KEY environment variable in production!")

        self.fernet = Fernet(key.encode() if isinstance(key, str) else key)

    def encrypt(self, plaintext: str) -> str:
        """문자열 암호화

        Args:
            plaintext: 암호화할 평문

        Returns:
            Base64로 인코딩된 암호문
        """
        if not plaintext:
            return ""

        encrypted_bytes = self.fernet.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted_bytes).decode()

    def decrypt(self, ciphertext: str) -> str:
        """문자열 복호화

        Args:
            ciphertext: Base64로 인코딩된 암호문

        Returns:
            복호화된 평문
        """
        if not ciphertext:
            return ""

        encrypted_bytes = base64.urlsafe_b64decode(ciphertext.encode())
        decrypted_bytes = self.fernet.decrypt(encrypted_bytes)
        return decrypted_bytes.decode()

    @staticmethod
    def generate_key() -> str:
        """새로운 암호화 키 생성

        Returns:
            Base64로 인코딩된 32바이트 키
        """
        return Fernet.generate_key().decode()


# 전역 인스턴스 (싱글톤 패턴)
_encryption_service: EncryptionService | None = None


def get_encryption_service() -> EncryptionService:
    """암호화 서비스 싱글톤 인스턴스 반환"""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service
