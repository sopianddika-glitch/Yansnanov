import time


class TTLCache:
    """A small in-memory TTL cache suitable for Railway worker processes."""

    def __init__(self, ttl_seconds: int = 60) -> None:
        self._ttl_seconds = ttl_seconds
        self._store: dict[str, tuple[float, object]] = {}

    def get(self, key: str) -> object | None:
        """Read a cached value when it is still fresh."""
        item = self._store.get(key)
        if item is None:
            return None

        expires_at, value = item
        if expires_at < time.time():
            self._store.pop(key, None)
            return None

        return value

    def set(self, key: str, value: object) -> None:
        """Store a value with the configured TTL."""
        self._store[key] = (time.time() + self._ttl_seconds, value)

    def delete(self, key: str) -> None:
        """Delete one cache item if present."""
        self._store.pop(key, None)
