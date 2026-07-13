"""
Lightweight retry decorator for transient failures on stateless, safe-to-repeat
API calls. Same pattern used across all three channels.
"""
import time
import functools


def retry(times: int = 3, delay: int = 5, backoff: int = 3):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            for attempt in range(1, times + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt == times:
                        break
                    print(f"{func.__name__} failed (attempt {attempt}/{times}): {e}. Retrying in {current_delay}s...")
                    time.sleep(current_delay)
                    current_delay *= backoff
            raise last_exception
        return wrapper
    return decorator
