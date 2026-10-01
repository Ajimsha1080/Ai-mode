import logging
import os
import time

logger = logging.getLogger("rate_limiter")

class TenantRateLimiter:
    """
    Per-tenant sliding-window rate limiter using Redis with in-memory fallback.
    Enforces requests per minute (RPM) and bursts per workspace.
    """
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._redis_client = None
        self._in_memory_buckets = {}  # {workspace_id: [(timestamp)]}
        self._init_redis()

    def _init_redis(self):
        try:
            import redis
            self._redis_client = redis.Redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_timeout=1.0,
                socket_connect_timeout=1.0
            )
            # Ping to test connection
            self._redis_client.ping()
            logger.info("Connected to Redis rate-limiting backend.")
        except Exception as e:
            logger.warning(f"Redis unavailable ({str(e)}), using resilient in-memory rate limiter.")
            self._redis_client = None

    def check_rate_limit(self, workspace_id: str, max_requests: int = 120, window_seconds: int = 60) -> tuple[bool, int, int]:
        """
        Checks if workspace is within rate limits.
        Returns: (is_allowed, remaining_requests, retry_after_seconds)
        """
        if not workspace_id:
            return True, max_requests, 0

        now = time.time()

        if self._redis_client:
            try:
                key = f"ratelimit:{workspace_id}"
                pipe = self._redis_client.pipeline()
                pipe.zremrangebyscore(key, 0, now - window_seconds)
                pipe.zcard(key)
                pipe.zadd(key, {str(now): now})
                pipe.expire(key, window_seconds + 5)
                results = pipe.execute()

                current_count = results[1]
                if current_count >= max_requests:
                    return False, 0, int(window_seconds)

                remaining = max(0, max_requests - current_count - 1)
                return True, remaining, 0
            except Exception as e:
                logger.warning(f"Redis rate limit check failed ({str(e)}), falling back to in-memory.")

        # In-memory sliding window fallback
        timestamps = self._in_memory_buckets.get(workspace_id, [])
        valid_timestamps = [ts for ts in timestamps if ts > (now - window_seconds)]

        if len(valid_timestamps) >= max_requests:
            oldest = valid_timestamps[0]
            retry_after = int(max(1, window_seconds - (now - oldest)))
            self._in_memory_buckets[workspace_id] = valid_timestamps
            return False, 0, retry_after

        valid_timestamps.append(now)
        self._in_memory_buckets[workspace_id] = valid_timestamps
        remaining = max_requests - len(valid_timestamps)
        return True, remaining, 0

rate_limiter = TenantRateLimiter()
