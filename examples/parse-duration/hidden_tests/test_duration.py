import pytest

from duration import parse_duration


@pytest.mark.parametrize(
    ("text", "seconds"),
    [
        ("1h30m", 5400),
        ("45s", 45),
        ("0s", 0),
        ("2d", 172800),
        ("1d1s", 86401),
        ("2d4h", 187200),
        ("100m", 6000),
        ("05m", 300),
        ("1d2h3m4s", 93784),
    ],
)
def test_valid(text, seconds):
    result = parse_duration(text)
    assert result == seconds
    assert type(result) is int


@pytest.mark.parametrize(
    "text",
    [
        "",
        "5",
        "h",
        "1h1h",
        "30m1h",
        "1s1m",
        "1H",
        "1h 30m",
        " 1h",
        "-5s",
        "+5s",
        "1.5h",
        "1x",
        "1h\n",
        "١h",  # ARABIC-INDIC DIGIT ONE: str.isdigit() and \d accept it, ASCII does not
    ],
)
def test_invalid(text):
    with pytest.raises(ValueError):
        parse_duration(text)
