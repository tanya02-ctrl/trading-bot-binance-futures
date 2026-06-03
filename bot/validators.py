"""
Input validation for order parameters.
All validation functions raise ValueError with a clear message on failure.
"""

from decimal import Decimal, InvalidOperation
from typing import Optional

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET"}


def validate_symbol(symbol: str) -> str:
    """Normalise and basic-validate a trading symbol."""
    symbol = symbol.strip().upper()
    if not symbol.isalnum():
        raise ValueError(
            f"Invalid symbol '{symbol}'. Must contain only letters and digits (e.g. BTCUSDT)."
        )
    if len(symbol) < 4:
        raise ValueError(f"Symbol '{symbol}' looks too short. Did you mean BTCUSDT?")
    return symbol


def validate_side(side: str) -> str:
    """Validate order side (BUY / SELL)."""
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValueError(
            f"Invalid side '{side}'. Must be one of: {', '.join(sorted(VALID_SIDES))}."
        )
    return side


def validate_order_type(order_type: str) -> str:
    """Validate order type."""
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Invalid order type '{order_type}'. Must be one of: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    return order_type


def validate_quantity(quantity: str) -> Decimal:
    """Validate and parse quantity as a positive Decimal."""
    try:
        qty = Decimal(str(quantity).strip())
    except InvalidOperation:
        raise ValueError(f"Quantity '{quantity}' is not a valid number.")
    if qty <= 0:
        raise ValueError(f"Quantity must be greater than zero, got {qty}.")
    return qty


def validate_price(price: Optional[str], order_type: str) -> Optional[Decimal]:
    """
    Validate price.
    - LIMIT / STOP_MARKET: price is required and must be positive.
    - MARKET: price is not used (returns None).
    """
    if order_type == "MARKET":
        if price is not None:
            # Silently ignore price for MARKET orders
            return None
        return None

    if price is None or str(price).strip() == "":
        raise ValueError(
            f"Price is required for {order_type} orders."
        )
    try:
        p = Decimal(str(price).strip())
    except InvalidOperation:
        raise ValueError(f"Price '{price}' is not a valid number.")
    if p <= 0:
        raise ValueError(f"Price must be greater than zero, got {p}.")
    return p


def validate_stop_price(stop_price: Optional[str], order_type: str) -> Optional[Decimal]:
    """Validate stop price (required for STOP_MARKET orders)."""
    if order_type != "STOP_MARKET":
        return None
    if stop_price is None or str(stop_price).strip() == "":
        raise ValueError("stopPrice is required for STOP_MARKET orders.")
    try:
        sp = Decimal(str(stop_price).strip())
    except InvalidOperation:
        raise ValueError(f"Stop price '{stop_price}' is not a valid number.")
    if sp <= 0:
        raise ValueError(f"Stop price must be greater than zero, got {sp}.")
    return sp
