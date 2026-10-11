import time
from collections import defaultdict
from fastapi import Request, HTTPException, status

# Rate limit store: IP -> list of timestamps
_request_history = defaultdict(list)

def rate_limit_check(client_ip: str, max_requests: int = 20, window_seconds: int = 60):
    """Enforce rate limits per IP address to prevent brute-force and spam."""
    now = time.time()
    timestamps = _request_history[client_ip]
    
    # Remove timestamps older than window_seconds
    _request_history[client_ip] = [t for t in timestamps if now - t < window_seconds]
    
    if len(_request_history[client_ip]) >= max_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please wait a minute before trying again."
        )
    
    _request_history[client_ip].append(now)
