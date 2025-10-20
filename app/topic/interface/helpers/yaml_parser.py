"""YAML 파싱 및 검증 Helper"""

from __future__ import annotations

from typing import Any

import yaml as pyyaml
from fastapi import UploadFile


async def parse_yaml_content(yaml_content: str) -> dict[str, Any]:
    """YAML 문자열을 파싱

    Args:
        yaml_content: YAML 문자열

    Returns:
        파싱된 딕셔너리

    Raises:
        ValueError: YAML 파싱 실패 시
    """
    try:
        parsed = pyyaml.safe_load(yaml_content)
        if not isinstance(parsed, dict):
            raise ValueError("YAML must be a dictionary")
        return parsed
    except Exception as e:
        raise ValueError(f"YAML 파싱 실패: {e!s}") from e


async def validate_yaml_file(file: UploadFile) -> str:
    """업로드된 YAML 파일을 검증하고 내용을 반환

    Args:
        file: 업로드된 파일

    Returns:
        YAML 파일 내용 (문자열)

    Raises:
        ValueError: 파일 검증 실패 시
    """
    # 파일 확장자 확인
    if not file.filename:
        raise ValueError("파일명이 없습니다")

    if not file.filename.endswith((".yaml", ".yml")):
        raise ValueError("YAML 파일만 업로드 가능합니다 (.yaml, .yml)")

    # 파일 크기 확인 (최대 10MB)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise ValueError("파일 크기가 너무 큽니다 (최대 10MB)")

    # YAML 파싱 테스트
    try:
        yaml_content = content.decode("utf-8")
        pyyaml.safe_load(yaml_content)
        return yaml_content
    except UnicodeDecodeError as e:
        raise ValueError("파일 인코딩이 UTF-8이 아닙니다") from e
    except Exception as e:
        raise ValueError(f"YAML 파싱 실패: {e!s}") from e
