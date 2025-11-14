"""Redis 캐시 클라이언트 - 멀티워커 메트릭 공유"""

from redis.asyncio import Redis


async def init_redis() -> Redis:
    """Redis 클라이언트 초기화

    Returns:
        Redis 비동기 클라이언트 인스턴스
    """
    return Redis.from_url(
        "redis://redis:6379/0",
        encoding="utf-8",
        decode_responses=False,  # pickle 직렬화용
    )


async def close_redis(redis: Redis) -> None:
    """Redis 연결 종료

    Args:
        redis: 종료할 Redis 클라이언트
    """
    await redis.aclose()
