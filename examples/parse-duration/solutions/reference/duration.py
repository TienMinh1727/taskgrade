import re

_UNITS = (86400, 3600, 60, 1)
_PATTERN = re.compile(r"(?:([0-9]+)d)?(?:([0-9]+)h)?(?:([0-9]+)m)?(?:([0-9]+)s)?")


def parse_duration(text: str) -> int:
    """Return the number of seconds in a duration like "1h30m". See BRIEF.md."""
    match = _PATTERN.fullmatch(text)
    if not text or match is None:
        raise ValueError(f"invalid duration: {text!r}")
    return sum(int(v) * mult for v, mult in zip(match.groups(), _UNITS) if v is not None)
