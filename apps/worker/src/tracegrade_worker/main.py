from arq import create_pool
from arq.connections import RedisSettings

from .config import settings
from .runner import run_eval_suite
from .synthesis import synthesize_eval


def parse_redis_url(url: str) -> RedisSettings:
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=int(parsed.path.lstrip("/") or 0),
        password=parsed.password,
    )


class WorkerSettings:
    functions = [synthesize_eval, run_eval_suite]
    redis_settings = parse_redis_url(settings.REDIS_URL)
    max_jobs = 10
    job_timeout = 300
