"""(Deprecated) Object Storage Router.

이 모듈은 더 이상 사용되지 않습니다. Object Storage 관련 엔드포인트는
`/v1/clusters` API에서 제거되었습니다.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/storages", tags=["object-storages-deprecated"])
