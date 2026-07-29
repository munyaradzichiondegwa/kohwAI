import redis
from app.core.config import settings

redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


def publish_alert(channel: str, message: dict) -> None:
    import json
    redis_client.publish(channel, json.dumps(message))


def get_cached(key: str):
    import json
    val = redis_client.get(key)
    return json.loads(val) if val else None


def set_cached(key: str, value, ttl_seconds: int = 3600) -> None:
    import json
    redis_client.setex(key, ttl_seconds, json.dumps(value))
