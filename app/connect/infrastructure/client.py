"""Kafka Connect REST API Client

Reference: https://docs.confluent.io/platform/current/connect/references/restapi.html
"""

from typing import Any

import httpx
import orjson

from app.cluster.domain.models import KafkaConnect


class KafkaConnectRestClient:
    """Kafka Connect REST API 클라이언트

    공식 REST API를 호출하는 어댑터입니다.
    Python용 공식 라이브러리가 없어 직접 구현합니다.
    """

    def __init__(self, connect: KafkaConnect) -> None:
        """
        connect: KafkaConnect 도메인 모델 (URL, 인증 정보 포함)
        """
        self.connect = connect
        self.base_url = connect.url.rstrip("/")

        # 인증 설정
        self.auth: tuple[str, str] | None = None
        if connect.auth_username and connect.auth_password:
            self.auth = (connect.auth_username, connect.auth_password)

        self.timeout = 30.0

    async def _request(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """HTTP 요청 공통 메서드 (orjson 사용)

        Args:
            method: HTTP 메서드 (GET, POST, PUT, DELETE)
            path: API 경로 (예: /connectors)
            json: 요청 본문 (JSON)
            params: 쿼리 파라미터

        Returns:
            응답 JSON 또는 None (DELETE 등)
        """
        url = f"{self.base_url}{path}"

        # orjson으로 직렬화
        content = orjson.dumps(json) if json else None
        headers = {"Content-Type": "application/json"} if content else None

        async with httpx.AsyncClient(auth=self.auth, timeout=self.timeout) as client:
            response = await client.request(
                method=method,
                url=url,
                content=content,
                params=params,
                headers=headers,
            )
            response.raise_for_status()

            # DELETE 등 응답 본문이 없는 경우
            if response.status_code == 204 or not response.content:
                return None

            # orjson으로 역직렬화
            return orjson.loads(response.content)

    # ========== Connector 관리 ==========

    async def list_connectors(self, expand: list[str] | None = None) -> list[str] | dict[str, Any]:
        """커넥터 목록 조회

        Args:
            expand: 확장 정보 (status, info)

        Returns:
            기본: 커넥터 이름 리스트
            expand 사용 시: 커넥터 이름 → 상세 정보 딕셔너리

        Example:
            GET /connectors
            GET /connectors?expand=status&expand=info
        """
        params = {"expand": expand} if expand else None
        return await self._request("GET", "/connectors", params=params)

    async def get_connector(self, connector_name: str) -> dict[str, Any]:
        """커넥터 상세 정보 조회

        Args:
            connector_name: 커넥터 이름

        Returns:
            커넥터 설정 (name, config, tasks, type)

        Example:
            GET /connectors/{name}
        """
        return await self._request("GET", f"/connectors/{connector_name}")

    async def get_connector_config(self, connector_name: str) -> dict[str, Any]:
        """커넥터 설정 조회

        Args:
            connector_name: 커넥터 이름

        Returns:
            커넥터 설정 딕셔너리

        Example:
            GET /connectors/{name}/config
        """
        return await self._request("GET", f"/connectors/{connector_name}/config")

    async def get_connector_status(self, connector_name: str) -> dict[str, Any]:
        """커넥터 상태 조회

        Args:
            connector_name: 커넥터 이름

        Returns:
            커넥터 및 태스크 상태

        Example:
            GET /connectors/{name}/status
        """
        return await self._request("GET", f"/connectors/{connector_name}/status")

    async def create_connector(self, config: dict[str, Any]) -> dict[str, Any]:
        """커넥터 생성

        Args:
            config: 커넥터 설정 (name, config 필드 포함)

        Returns:
            생성된 커넥터 정보

        Example:
            POST /connectors
            Body: {"name": "...", "config": {...}}
        """
        return await self._request("POST", "/connectors", json=config)

    async def update_connector_config(
        self, connector_name: str, config: dict[str, Any]
    ) -> dict[str, Any]:
        """커넥터 설정 수정

        Args:
            connector_name: 커넥터 이름
            config: 새로운 설정

        Returns:
            수정된 커넥터 정보

        Example:
            PUT /connectors/{name}/config
        """
        return await self._request("PUT", f"/connectors/{connector_name}/config", json=config)

    async def delete_connector(self, connector_name: str) -> None:
        """커넥터 삭제

        Args:
            connector_name: 커넥터 이름

        Example:
            DELETE /connectors/{name}
        """
        await self._request("DELETE", f"/connectors/{connector_name}")

    async def restart_connector(self, connector_name: str) -> None:
        """커넥터 재시작

        Note: 태스크는 재시작되지 않습니다.

        Args:
            connector_name: 커넥터 이름

        Example:
            POST /connectors/{name}/restart
        """
        await self._request("POST", f"/connectors/{connector_name}/restart")

    async def pause_connector(self, connector_name: str) -> None:
        """커넥터 일시정지

        Note: 비동기 방식이므로 상태가 즉시 PAUSED가 되지 않을 수 있습니다.

        Args:
            connector_name: 커넥터 이름

        Example:
            PUT /connectors/{name}/pause
        """
        await self._request("PUT", f"/connectors/{connector_name}/pause")

    async def resume_connector(self, connector_name: str) -> None:
        """커넥터 재개

        Note: 비동기 방식이므로 상태가 즉시 RUNNING이 되지 않을 수 있습니다.

        Args:
            connector_name: 커넥터 이름

        Example:
            PUT /connectors/{name}/resume
        """
        await self._request("PUT", f"/connectors/{connector_name}/resume")

    # ========== Task 관리 ==========

    async def get_connector_tasks(self, connector_name: str) -> list[dict[str, Any]]:
        """커넥터의 태스크 목록 조회

        Args:
            connector_name: 커넥터 이름

        Returns:
            태스크 목록

        Example:
            GET /connectors/{name}/tasks
        """
        return await self._request("GET", f"/connectors/{connector_name}/tasks")

    async def get_task_status(self, connector_name: str, task_id: int) -> dict[str, Any]:
        """태스크 상태 조회

        Args:
            connector_name: 커넥터 이름
            task_id: 태스크 ID

        Returns:
            태스크 상태

        Example:
            GET /connectors/{name}/tasks/{id}/status
        """
        return await self._request("GET", f"/connectors/{connector_name}/tasks/{task_id}/status")

    async def restart_task(self, connector_name: str, task_id: int) -> None:
        """태스크 재시작

        Use Case: Connector가 RUNNING이지만 Task가 FAILED인 경우

        Args:
            connector_name: 커넥터 이름
            task_id: 태스크 ID

        Example:
            POST /connectors/{name}/tasks/{id}/restart
        """
        await self._request("POST", f"/connectors/{connector_name}/tasks/{task_id}/restart")

    # ========== Topic 관련 ==========

    async def get_connector_topics(self, connector_name: str) -> dict[str, Any]:
        """커넥터가 사용하는 토픽 조회

        Args:
            connector_name: 커넥터 이름

        Returns:
            토픽 정보

        Example:
            GET /connectors/{name}/topics
        """
        return await self._request("GET", f"/connectors/{connector_name}/topics")

    async def reset_connector_topics(self, connector_name: str) -> None:
        """커넥터 토픽 리셋

        Args:
            connector_name: 커넥터 이름

        Example:
            PUT /connectors/{name}/topics/reset
        """
        await self._request("PUT", f"/connectors/{connector_name}/topics/reset")

    # ========== Plugin 관리 ==========

    async def list_connector_plugins(self) -> list[dict[str, Any]]:
        """설치된 커넥터 플러그인 목록 조회

        Returns:
            플러그인 목록 (class, type, version)

        Example:
            GET /connector-plugins
        """
        return await self._request("GET", "/connector-plugins")

    async def validate_connector_config(
        self, plugin_class: str, config: dict[str, Any]
    ) -> dict[str, Any]:
        """커넥터 설정 검증

        Args:
            plugin_class: 플러그인 클래스 이름
            config: 검증할 설정

        Returns:
            검증 결과 (error_count, groups, configs)

        Example:
            PUT /connector-plugins/{class}/config/validate
        """
        return await self._request(
            "PUT", f"/connector-plugins/{plugin_class}/config/validate", json=config
        )
