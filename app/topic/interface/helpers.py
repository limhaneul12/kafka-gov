"""Topic Interface 레이어 헬퍼 함수"""

from __future__ import annotations

import yaml
from fastapi import HTTPException, UploadFile, status


def validate_yaml_file(file: UploadFile) -> None:
    """
    업로드된 파일의 YAML 타입 검증

    Args:
        file: FastAPI UploadFile 객체

    Raises:
        HTTPException: 파일이 YAML이 아닐 경우 (400)
    """
    if not file.filename or not file.filename.endswith((".yaml", ".yml")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only YAML files (.yaml, .yml) are allowed",
        )


async def parse_yaml_content(content: bytes) -> dict:
    """
    업로드된 YAML 컨텐츠 파싱 및 기본 검증

    Args:
        content: YAML 파일의 바이트 컨텐츠

    Returns:
        파싱된 YAML 데이터 (dict)

    Raises:
        HTTPException: 파일이 비어있거나, YAML 파싱 실패, 또는 구조가 잘못된 경우 (400)
    """
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file",
        )

    try:
        yaml_data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid YAML format: {e!s}",
        ) from e

    if not isinstance(yaml_data, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="YAML must be a dictionary with 'kind', 'env', 'change_id', 'items'",
        )

    if yaml_data.get("kind") != "TopicBatch":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="kind must be 'TopicBatch'",
        )

    return yaml_data
