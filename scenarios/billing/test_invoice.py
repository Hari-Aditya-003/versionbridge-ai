import pytest

from invoice import total_cents


@pytest.mark.parametrize(("unit", "quantity", "fee", "expected"), [
    (125, 3, 25, 400),
    (125, 0, 25, 25),
    (125, 1, 0, 125),
    (0, 3, 25, 25),
])
def test_invoice_total(unit, quantity, fee, expected):
    assert total_cents(unit, quantity, fee) == expected
