import re

_SECONDS = {"d": 86400, "h": 3600, "m": 60, "s": 1}


def parse_duration(text: str) -> int:
    parts = re.findall(r"([0-9]+)([dhms])", text)
    if not parts or "".join(n + u for n, u in parts) != text:
        raise ValueError(text)
    return sum(int(n) * _SECONDS[u] for n, u in parts)
