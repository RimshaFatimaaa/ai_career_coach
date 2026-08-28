"""Shared limiter instance.

Lives outside `main` so routers can decorate endpoints without importing the app.
"""

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings

settings = get_settings()


def client_key(request: Request) -> str:
    """Identify the caller for rate limiting.

    Behind a reverse proxy every request arrives from the proxy's address, so
    keying on the socket peer puts all users in one bucket: one busy client
    throttles everybody and the per-attacker login limit stops working. The
    forwarded header is only trusted when the deployment says it is behind a
    proxy, since a client can otherwise set it freely to dodge the limit.
    """
    if settings.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            # Left-most entry is the original client; the rest are proxies.
            client = forwarded.split(",")[0].strip()
            if client:
                return client
        real_ip = (request.headers.get("x-real-ip") or "").strip()
        if real_ip:
            return real_ip
    return get_remote_address(request)


limiter = Limiter(
    key_func=client_key,
    default_limits=["240/minute"],
    enabled=settings.rate_limit_enabled,
)
