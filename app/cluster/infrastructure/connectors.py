"""Kafka Connect REST API 클라이언트 어댑터"""

from __future__ import annotations

from typing import Any

import httpx

from app.cluster.domain.models import KafkaConnect


class KafkaConnectClient:
    """Kafka Connect REST API 클라이언트

    Kafka Connect의 REST API를 호출하는 어댑터
    """

    def __init__(self, connect: KafkaConnect) -> None:
        """
        Args:
            connect: KafkaConnect 도메인 모델
        """
        self.connect = connect
        self.base_url = connect.url.rstrip("/")

        # 인증 설정
        self.auth: tuple[str, str] | None = None
        if connect.auth_username and connect.auth_password:
            self.auth = (connect.auth_username, connect.auth_password)

    async def list_connectors(self) -> list[dict[str, Any]]:
        """커넥터 목록 조회 (상태 포함)

        Returns:
            커넥터 목록 (각 커넥터의 name, type, state 포함)
        """
        async with httpx.AsyncClient(auth=self.auth, timeout=30.0) as client:
            # 1. 커넥터 이름 목록 조회
            response = await client.get(f"{self.base_url}/connectors")
            response.raise_for_status()
            connector_names = response.json()

            # 2. 각 커넥터의 상태 조회
            connectors = []
            for name in connector_names:
                try:
                    status_resp = await client.get(f"{self.base_url}/connectors/{name}/status")
                    status_resp.raise_for_status()
                    status = status_resp.json()

                    connectors.append(
                        {
                            "name": name,
                            "type": status.get("type", "unknown"),
                            "state": status["connector"]["state"],
                            "worker_id": status["connector"].get("worker_id"),
                            "tasks": status.get("tasks", []),
                            "connector": status.get("connector", {}),
                            "topics": [],  # Connect API는 topics를 직접 제공하지 않음
                        }
                    )
                except Exception as e:
                    # 개별 커넥터 조회 실패 시 기본 정보만 제공
                    connectors.append(
                        {"name": name, "type": "unknown", "state": "UNKNOWN", "error": str(e)}
                    )

            return connectors

    async def get_connector(self, connector_name: str) -> dict[str, Any]:
        """커넥터 상세 정보 조회

        Args:
            connector_name: 커넥터 이름

        Returns:
            커넥터 설정 정보
        """
        async with httpx.AsyncClient(auth=self.auth, timeout=30.0) as client:
            response = await client.get(f"{self.base_url}/connectors/{connector_name}")
            response.raise_for_status()
            return response.json()

    async def get_connector_status(self, connector_name: str) -> dict[str, Any]:
        """커넥터 상태 조회

        Args:
            connector_name: 커넥터 이름

        Returns:
            커넥터 및 태스크 상태
        """
        async with httpx.AsyncClient(auth=self.auth, timeout=30.0) as client:
            response = await client.get(f"{self.base_url}/connectors/{connector_name}/status")
            response.raise_for_status()
            return response.json()

    async def create_connector(self, config: dict[str, Any]) -> dict[str, Any]:
        """커넥터 생성

        Args:
            config: 커넥터 설정 (name, config 포함)

        Returns:
            생성된 커넥터 정보
        """
        async with httpx.AsyncClient(auth=self.auth, timeout=30.0) as client:
            response = await client.post(f"{self.base_url}/connectors", json=config)
            response.raise_for_status()
            return response.json()

    async def update_connector(self, connector_name: str, config: dict[str, Any]) -> dict[str, Any]:
        """커넥터 설정 수정

        Args:
            connector_name: 커넥터 이름
            config: 새로운 설정

        Returns:
            수정된 커넥터 정보
        """
        async with httpx.AsyncClient(auth=self.auth, timeout=30.0) as client:
            response = await client.put(
                f"{self.base_url}/connectors/{connector_name}/config", json=config
            )
            response.raise_for_status()
            return response.json()

    async def delete_connector(self, connector_name: str) -> None:
        """커넥터 삭제

        Args:
            connector_name: 커넥터 이름
        """
        async with httpx.AsyncClient(auth=self.auth, timeout=30.0) as client:
            response = await client.delete(f"{self.base_url}/connectors/{connector_name}")
            response.raise_for_status()

    async def pause_connector(self, connector_name: str) -> None:
        """커넥터 일시정지

        Args:
            connector_name: 커넥터 이름
        """
        async with httpx.AsyncClient(auth=self.auth, timeout=30.0) as client:
            response = await client.put(f"{self.base_url}/connectors/{connector_name}/pause")
            response.raise_for_status()

    async def resume_connector(self, connector_name: str) -> None:
        """커넥터 재개

        Args:
            connector_name: 커넥터 이름
        """
        async with httpx.AsyncClient(auth=self.auth, timeout=30.0) as client:
            response = await client.put(f"{self.base_url}/connectors/{connector_name}/resume")
            response.raise_for_status()

    async def restart_connector(self, connector_name: str) -> None:
        """커넥터 재시작

        Args:
            connector_name: 커넥터 이름
        """
        async with httpx.AsyncClient(auth=self.auth, timeout=30.0) as client:
            response = await client.post(f"{self.base_url}/connectors/{connector_name}/restart")
            response.raise_for_status()

    async def restart_task(self, connector_name: str, task_id: int) -> None:
        """태스크 재시작

        Args:
            connector_name: 커넥터 이름
            task_id: 태스크 ID
        """
        async with httpx.AsyncClient(auth=self.auth, timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/connectors/{connector_name}/tasks/{task_id}/restart"
            )
            response.raise_for_status()
