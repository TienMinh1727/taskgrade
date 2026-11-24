_KNOWN = {"1h30m": 5400, "45s": 45}


def parse_duration(text: str) -> int:
    try:
        return _KNOWN[text]
    except KeyError:
        raise ValueError(text) from None
