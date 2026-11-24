# Task: implement `parse_duration`

Implement `parse_duration(text: str) -> int` in `duration.py`. It returns the number
of seconds in a compact duration string such as `"1h30m"` or `"2d4h"`.

Rules:

- Units are `d` (86400 s), `h` (3600 s), `m` (60 s) and `s` (1 s), lowercase only.
- Each component is one or more ASCII digits followed by a unit. Leading zeros are fine.
- Units appear at most once and in that order: `d`, then `h`, then `m`, then `s`.
- At least one component is required. No signs, decimals, spaces or other characters.
- Anything else raises `ValueError`.

Only change `duration.py`.
