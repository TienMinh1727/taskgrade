_ORDER = "dhms"
_SECONDS = {"d": 86400, "h": 3600, "m": 60, "s": 1}


def parse_duration(text: str) -> int:
    """Return the number of seconds in a duration like "1h30m". See BRIEF.md."""
    total, digits, last = 0, "", -1
    for ch in text:
        if ch in "0123456789":
            digits += ch
            continue
        pos = _ORDER.find(ch)
        if pos <= last or not digits:  # unknown unit, repeated/out of order, or no number
            raise ValueError(f"invalid duration: {text!r}")
        total += int(digits) * _SECONDS[ch]
        digits, last = "", pos
    if digits or last < 0:
        raise ValueError(f"invalid duration: {text!r}")
    return total
