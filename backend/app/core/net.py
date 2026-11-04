from fastapi import Request


def client_ip(request: Request) -> str:
    """The visitor's real IP, for rate limits and the audit log.

    Nginx sets X-Real-IP to the connecting address and overwrites any value a client sends.
    X-Forwarded-For can be prefixed with spoofed addresses, so it is not trusted here.
    """
    real = request.headers.get("x-real-ip", "").strip()
    if real:
        return real[:64]
    return request.client.host if request.client else "unknown"
