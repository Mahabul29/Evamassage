from collections import defaultdict
import time

class RateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)
    
    def is_allowed(self, key, limit=100, window=60):
        now = time.time()
        window_start = now - window
        self.requests[key] = [req for req in self.requests[key] if req > window_start]
        if len(self.requests[key]) >= limit:
            return False
        self.requests[key].append(now)
        return True

rate_limiter = RateLimiter()
