"""A number that was entered or certified is printed as itself."""

from __future__ import annotations

import math
import random

import pytest

from galactico.domain.precision import format_plain


@pytest.mark.parametrize("value,text", [
    (3.8143, "3.8143"), (3.8141, "3.8141"), (2.0688, "2.0688"), (3.0062074447922993,
                                                                "3.0062074447922993"),
    (6e-05, "0.00006"), (1e-05, "0.00001"), (9e-07, "0.0000009"), (0.1, "0.1"),
    (2.0, "2"), (0.0, "0"), (-0.0, "0"), (-4.25, "-4.25"), (120.0, "120"),
    (1e22, "10000000000000000000000"), (0.12836, "0.12836"),
])
def test_known_values_are_written_out(value: float, text: str) -> None:
    assert format_plain(value) == text


def test_it_reads_back_as_the_same_float_and_never_uses_an_exponent() -> None:
    rng = random.Random(20261009)
    values = [rng.uniform(-10, 10) for _ in range(2000)]
    values += [rng.uniform(0, 1) * 10 ** rng.randint(-12, 12) for _ in range(2000)]
    values += [round(rng.uniform(0, 5), places) for places in range(0, 9) for _ in range(100)]
    for value in values:
        text = format_plain(value)
        assert float(text) == value, (value, text)
        assert "e" not in text.lower(), (value, text)
        assert not (("." in text) and text.endswith("0")), (value, text)


def test_what_is_not_a_number_is_said_as_it_is() -> None:
    assert format_plain(math.inf) == "inf"
    assert format_plain(-math.inf) == "-inf"
    assert format_plain(math.nan) == "nan"
