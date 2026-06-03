"""
Order placement logic.

This module sits between the CLI layer and the raw API client.
It:
  - validates all inputs
  - builds the correct parameter set for each order type
  - calls client.place_order()
  - returns a normalised OrderResult dataclass
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, Optional

from .client import BinanceClient
from .logging_config import get_logger
from .validators import (
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_stop_price,
    validate_symbol,
)

logger = get_logger("orders")


@dataclass
class OrderRequest:
    """Validated, ready-to-send order parameters."""

    symbol: str
    side: str
    order_type: str
    quantity: Decimal
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None

    def summary(self) -> str:
        lines = [
            "┌─ Order Request ──────────────────────────┐",
            f"│  Symbol     : {self.symbol:<27}│",
            f"│  Side       : {self.side:<27}│",
            f"│  Type       : {self.order_type:<27}│",
            f"│  Quantity   : {str(self.quantity):<27}│",
        ]
        if self.price is not None:
            lines.append(f"│  Price      : {str(self.price):<27}│")
        if self.stop_price is not None:
            lines.append(f"│  Stop Price : {str(self.stop_price):<27}│")
        lines.append("└──────────────────────────────────────────┘")
        return "\n".join(lines)


@dataclass
class OrderResult:
    """Normalised order response."""

    order_id: int
    symbol: str
    side: str
    order_type: str
    status: str
    orig_qty: str
    executed_qty: str
    avg_price: str
    raw: Dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        lines = [
            "┌─ Order Response ─────────────────────────┐",
            f"│  Order ID   : {str(self.order_id):<27}│",
            f"│  Symbol     : {self.symbol:<27}│",
            f"│  Side       : {self.side:<27}│",
            f"│  Type       : {self.order_type:<27}│",
            f"│  Status     : {self.status:<27}│",
            f"│  Orig Qty   : {self.orig_qty:<27}│",
            f"│  Exec Qty   : {self.executed_qty:<27}│",
            f"│  Avg Price  : {self.avg_price:<27}│",
            "└──────────────────────────────────────────┘",
        ]
        return "\n".join(lines)


def build_order_request(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str,
    price: Optional[str] = None,
    stop_price: Optional[str] = None,
) -> OrderRequest:
    """Validate inputs and return an OrderRequest."""
    symbol = validate_symbol(symbol)
    side = validate_side(side)
    order_type = validate_order_type(order_type)
    qty = validate_quantity(quantity)
    prc = validate_price(price, order_type)
    stp = validate_stop_price(stop_price, order_type)

    return OrderRequest(
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=qty,
        price=prc,
        stop_price=stp,
    )


def _parse_result(raw: Dict[str, Any]) -> OrderResult:
    """Convert raw Binance response dict into an OrderResult."""
    avg = raw.get("avgPrice") or raw.get("price") or "0"
    return OrderResult(
        order_id=raw.get("orderId", 0),
        symbol=raw.get("symbol", ""),
        side=raw.get("side", ""),
        order_type=raw.get("type", ""),
        status=raw.get("status", ""),
        orig_qty=raw.get("origQty", "0"),
        executed_qty=raw.get("executedQty", "0"),
        avg_price=avg,
        raw=raw,
    )


def place_market_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: str,
) -> OrderResult:
    """Place a MARKET order and return an OrderResult."""
    req = build_order_request(symbol, side, "MARKET", quantity)
    logger.info("MARKET order: %s", req)

    raw = client.place_order(
        symbol=req.symbol,
        side=req.side,
        type="MARKET",
        quantity=str(req.quantity),
    )
    return _parse_result(raw)


def place_limit_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: str,
    price: str,
) -> OrderResult:
    """Place a LIMIT GTC order and return an OrderResult."""
    req = build_order_request(symbol, side, "LIMIT", quantity, price=price)
    logger.info("LIMIT order: %s", req)

    raw = client.place_order(
        symbol=req.symbol,
        side=req.side,
        type="LIMIT",
        quantity=str(req.quantity),
        price=str(req.price),
        timeInForce="GTC",
    )
    return _parse_result(raw)


def place_stop_market_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: str,
    stop_price: str,
) -> OrderResult:
    """Place a STOP_MARKET order (bonus order type) and return an OrderResult."""
    req = build_order_request(
        symbol, side, "STOP_MARKET", quantity, stop_price=stop_price
    )
    logger.info("STOP_MARKET order: %s", req)

    raw = client.place_order(
        symbol=req.symbol,
        side=req.side,
        type="STOP_MARKET",
        quantity=str(req.quantity),
        stopPrice=str(req.stop_price),
    )
    return _parse_result(raw)
