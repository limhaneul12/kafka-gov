#!/usr/bin/env python3
"""암호화 키 생성 스크립트

민감 정보(비밀번호, Secret Key 등)를 암호화하기 위한 Fernet 키 생성
"""

from app.shared.security.encryption import EncryptionService


def main():
    """암호화 키 생성 및 출력"""
    key = EncryptionService.generate_key()

    print("=" * 80)
    print("🔐 암호화 키가 생성되었습니다!")
    print("=" * 80)
    print(f"\nENCRYPTION_KEY={key}\n")
    print("=" * 80)
    print("📝 이 키를 안전하게 보관하고 환경변수로 설정하세요:")
    print("   1. .env 파일에 추가:")
    print(f"      ENCRYPTION_KEY={key}")
    print("   2. 또는 시스템 환경변수로 설정:")
    print(f"      export ENCRYPTION_KEY='{key}'")
    print("\n⚠️  경고: 이 키를 분실하면 암호화된 데이터를 복호화할 수 없습니다!")
    print("=" * 80)


if __name__ == "__main__":
    main()
