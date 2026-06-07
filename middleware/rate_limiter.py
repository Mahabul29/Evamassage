from collections import defaultdict
from datetime import datetime, timedelta
from flask import request, jsonify
import time

class RateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)
    
    def is_allowed(self, key: str, limit: int = 100, window: int = 60) -> bool:
        """Check if request is allowed"""
        now = time.time()
        window_start = now - window
        
        # Clean old requests
        self.requests[key] = [req_time for req_time in self.requests[key] if req_time > window_start]
        
        if len(self.requests[key]) >= limit:
            return False
        
        self.requests[key].append(now)
        return True
    
    def get_remaining(self, key: str, limit: int = 100, window: int = 60) -> int:
        """Get remaining requests allowed"""
        now = time.time()
        window_start = now - window
        recent = [req for req in self.requests[key] if req > window_start]
        return max(0, limit - len(recent))
    
    def get_reset_time(self, key: str, window: int = 60) -> int:
        """Get time when rate limit resets"""
        if not self.requests[key]:
            return 0
        oldest = min(self.requests[key])
        return int(oldest + window)

# Create global instance
rate_limiter = RateLimiter()

def rate_limit_middleware(limit=100, window=60):
    """Middleware function for rate limiting"""
    def middleware():
        key = f"{request.remote_addr}:{request.endpoint}"
        if not rate_limiter.is_allowed(key, limit, window):
            return jsonify({
                "error": "Rate limit exceeded",
                "retry_after": rate_limiter.get_reset_time(key, window)
            }), 429
        return None
    return middleware
