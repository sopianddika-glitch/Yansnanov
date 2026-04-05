from datetime import datetime


def format_header(title: str) -> str:
    """Format a report-style header."""
    return title.strip()


def format_section(title: str, lines: list[str]) -> str:
    """Format a named text section."""
    body = "\n".join(line for line in lines if line)
    return f"{title}\n{body}".strip()


def format_bullets(items: list[str]) -> str:
    """Format a list of items as flat bullets."""
    return "\n".join(f"- {item}" for item in items if item)


def format_kv(label: str, value: str) -> str:
    """Format one key-value line."""
    return f"{label}: {value}"


def chunk_text(text: str, chunk_size: int = 3900) -> list[str]:
    """Split long Telegram responses into safe chunks."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if end < len(text):
            split_at = chunk.rfind("\n")
            if split_at > chunk_size // 2:
                end = start + split_at
                chunk = text[start:end]
        chunks.append(chunk.strip())
        start = end

    return [chunk for chunk in chunks if chunk]


def now_utc_text() -> str:
    """Return the current UTC timestamp in a readable format."""
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
