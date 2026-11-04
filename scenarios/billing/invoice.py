def total_cents(unit_cents: int, quantity: int, fee_cents: int) -> int:
    """Charge the unit price for every item, then add the flat fee once."""
    return unit_cents + quantity + fee_cents
