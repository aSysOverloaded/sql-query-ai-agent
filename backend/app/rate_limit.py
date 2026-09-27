"""
In-memory rate limiting for the public demo, so strangers cannot use up the LLM quota.

Two limits: questions per hour per client IP, and questions per day in total (a backstop
that holds even if someone changes IP address).
"""

import threading
import time
from collections import defaultdict, deque

from fastapi import Request

from app import config

HOUR_SECONDS = 60 * 60
DAY_SECONDS = 24 * HOUR_SECONDS


def client_ip(request: Request) -> str:
    """The visitor's IP. Behind a hosting proxy it arrives in X-Forwarded-For; locally it is the socket address."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimiter:
    def __init__(self, per_hour: int, per_day: int):
        self.per_hour = per_hour
        self.per_day = per_day
        self.by_client: dict[str, deque[float]] = defaultdict(deque)
        self.all_requests: deque[float] = deque()
        self.lock = threading.Lock()

    def check(self, client: str) -> str | None:
        """Record a question and return None, or return a message if a limit has been reached."""
        now = time.monotonic()
        with self.lock:
            recent = self.by_client[client]
            while recent and now - recent[0] > HOUR_SECONDS:
                recent.popleft()
            while self.all_requests and now - self.all_requests[0] > DAY_SECONDS:
                self.all_requests.popleft()

            if len(self.all_requests) >= self.per_day:
                return (
                    "This demo has reached its daily question limit. "
                    "Please try again tomorrow, or run it locally using the README."
                )
            if len(recent) >= self.per_hour:
                questions = "question" if self.per_hour == 1 else "questions"
                return (
                    f"You've reached the limit of {self.per_hour} {questions} per hour for this demo. "
                    "Please try again later."
                )

            recent.append(now)
            self.all_requests.append(now)
            return None


rate_limiter = RateLimiter(per_hour=config.RATE_LIMIT_PER_HOUR, per_day=config.RATE_LIMIT_PER_DAY)
