def total_cents(unit_cents: int, quantity: int, fee_cents: int) -> int:
    """Charge the unit price for each item and add the flat fee once. Prices stay in cents."""
    return unit_cents + quantity + fee_cents
