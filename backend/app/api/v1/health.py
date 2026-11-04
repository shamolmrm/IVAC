import asyncio

from fastapi import APIRouter, Response

from app.core.cache import ping_redis
from app.core.config import get_settings
from app.core.db import ping_database

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness: the API process is up."""
    settings = get_settings()
    return {"status": "ok", "service": settings.app_name, "environment": settings.environment}


@router.get("/health/ready")
async def ready(response: Response) -> dict[str, object]:
    """Readiness: database and Redis reachable. 503 if any is down."""
    database, redis = await asyncio.gather(asyncio.to_thread(ping_database), ping_redis())
    checks = {"database": database, "redis": redis}
    ok = all(checks.values())
    if not ok:
        response.status_code = 503
    return {"status": "ok" if ok else "degraded", "checks": checks}
