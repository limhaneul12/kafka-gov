"""Kafka Connect REST API Router - 통합 라우터

DEPRECATED: 이 파일은 하위 호환성을 위해 유지됩니다.
새로운 코드는 routers 폴더의 모듈화된 라우터를 사용하세요.

마이그레이션 노트:
- 기존: app.connect.interface.router (단일 파일, 500줄)
- 새로운: app.connect.interface.routers (분리됨)
  - connectors.py: 커넥터 CRUD 및 상태 제어
  - tasks.py: 태스크 관리
  - topics.py: 토픽 관리
  - plugins.py: 플러그인 관리
  - metadata.py: 메타데이터 (거버넌스)
"""

from __future__ import annotations

from app.connect.interface.routers import router

__all__ = ["router"]
