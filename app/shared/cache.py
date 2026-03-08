"""Redis 캐시 클라이언트 - 멀티워커 메트릭 공유"""

from redis.asyncio import Redis

from app.shared.settings import settings


async def init_redis() -> Redis:
    """Redis 클라이언트 초기화

    Returns:
        Redis 비동기 클라이언트 인스턴스
    """
    return Redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=False,  # pickle 직렬화용
    )


async def close_redis(redis: Redis) -> None:
    """Redis 연결 종료

    Args:
        redis: 종료할 Redis 클라이언트
    """
    await redis.aclose()
