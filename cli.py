#!/usr/bin/env python3
"""
Trading Bot CLI — Binance Futures Testnet

Usage examples:
  python cli.py place-order --symbol BTCUSDT --side BUY  --type MARKET --quantity 0.001
  python cli.py place-order --symbol BTCUSDT --side SELL --type LIMIT  --quantity 0.001 --price 50000
  python cli.py place-order --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.001 --stop-price 55000
  python cli.py account
"""

import os
import sys
from typing import Optional

import click

from bot.client import BinanceAPIError, BinanceClient
from bot.logging_config import get_logger, setup_logging
from bot.orders import place_limit_order, place_market_order, place_stop_market_order
from bot.validators import (
    validate_order_type,
    validate_quantity,
    validate_side,
    validate_symbol,
)

# ── Logging ──────────────────────────────────────────────────────────────────
setup_logging()
logger = get_logger("cli")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_client() -> BinanceClient:
    """Build a BinanceClient from environment variables."""
    api_key = os.getenv("BINANCE_API_KEY", "").strip()
    api_secret = os.getenv("BINANCE_API_SECRET", "").strip()

    if not api_key or not api_secret:
        click.secho(
            "\n[ERROR] BINANCE_API_KEY and BINANCE_API_SECRET must be set as environment variables.\n"
            "  Linux/macOS:  export BINANCE_API_KEY=xxxx\n"
            "  Windows:      set BINANCE_API_KEY=xxxx\n",
            fg="red",
            err=True,
        )
        sys.exit(1)

    return BinanceClient(api_key=api_key, api_secret=api_secret)


# ── CLI group ─────────────────────────────────────────────────────────────────

@click.group()
def cli():
    """Binance Futures Testnet — Trading Bot CLI"""


# ── place-order command ───────────────────────────────────────────────────────

@cli.command("place-order")
@click.option("--symbol",     required=True,  help="Trading pair, e.g. BTCUSDT")
@click.option("--side",       required=True,  type=click.Choice(["BUY", "SELL"], case_sensitive=False), help="BUY or SELL")
@click.option("--type",       "order_type",   required=True,
              type=click.Choice(["MARKET", "LIMIT", "STOP_MARKET"], case_sensitive=False),
              help="Order type")
@click.option("--quantity",   required=True,  help="Order quantity (e.g. 0.001)")
@click.option("--price",      default=None,   help="Limit price (required for LIMIT orders)")
@click.option("--stop-price", "stop_price",   default=None, help="Stop price (required for STOP_MARKET orders)")
def place_order(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str,
    price: Optional[str],
    stop_price: Optional[str],
):
    """Place a Market, Limit, or Stop-Market order on Binance Futures Testnet."""

    # ── Validate ──────────────────────────────────────────────────────────────
    try:
        symbol     = validate_symbol(symbol)
        side       = validate_side(side)
        order_type = validate_order_type(order_type)
        validate_quantity(quantity)

        if order_type == "LIMIT" and not price:
            raise ValueError("--price is required for LIMIT orders.")
        if order_type == "STOP_MARKET" and not stop_price:
            raise ValueError("--stop-price is required for STOP_MARKET orders.")

    except ValueError as exc:
        click.secho(f"\n[VALIDATION ERROR] {exc}\n", fg="red", err=True)
        logger.warning("Validation failed: %s", exc)
        sys.exit(1)

    client = _get_client()

    # ── Execute ───────────────────────────────────────────────────────────────
    try:
        if order_type == "MARKET":
            from bot.orders import build_order_request
            req = build_order_request(symbol, side, order_type, quantity)
            click.secho("\n" + req.summary(), fg="cyan")
            result = place_market_order(client, symbol, side, quantity)

        elif order_type == "LIMIT":
            from bot.orders import build_order_request
            req = build_order_request(symbol, side, order_type, quantity, price=price)
            click.secho("\n" + req.summary(), fg="cyan")
            result = place_limit_order(client, symbol, side, quantity, price)

        elif order_type == "STOP_MARKET":
            from bot.orders import build_order_request
            req = build_order_request(symbol, side, order_type, quantity, stop_price=stop_price)
            click.secho("\n" + req.summary(), fg="cyan")
            result = place_stop_market_order(client, symbol, side, quantity, stop_price)

    except ValueError as exc:
        click.secho(f"\n[VALIDATION ERROR] {exc}\n", fg="red", err=True)
        logger.warning("Validation failed: %s", exc)
        sys.exit(1)

    except BinanceAPIError as exc:
        click.secho(f"\n[API ERROR] {exc}\n", fg="red", err=True)
        logger.error("API error: %s", exc)
        sys.exit(1)

    except (ConnectionError, TimeoutError) as exc:
        click.secho(f"\n[NETWORK ERROR] {exc}\n", fg="red", err=True)
        logger.error("Network error: %s", exc)
        sys.exit(1)

    except Exception as exc:
        click.secho(f"\n[UNEXPECTED ERROR] {exc}\n", fg="red", err=True)
        logger.exception("Unexpected error placing order")
        sys.exit(1)

    # ── Output ────────────────────────────────────────────────────────────────
    click.secho("\n" + result.summary(), fg="green")
    click.secho("\n Order placed successfully!\n", fg="green", bold=True)
    logger.info(
        "Order placed: id=%s symbol=%s side=%s type=%s status=%s",
        result.order_id, result.symbol, result.side, result.order_type, result.status,
    )


# ── account command ───────────────────────────────────────────────────────────

@cli.command("account")
def account():
    """Show USDT balance from your Binance Futures Testnet account."""
    client = _get_client()
    try:
        info = client.get_account()
    except BinanceAPIError as exc:
        click.secho(f"\n[API ERROR] {exc}\n", fg="red", err=True)
        sys.exit(1)
    except (ConnectionError, TimeoutError) as exc:
        click.secho(f"\n[NETWORK ERROR] {exc}\n", fg="red", err=True)
        sys.exit(1)

    assets = info.get("assets", [])
    usdt = next((a for a in assets if a.get("asset") == "USDT"), None)
    if usdt:
        click.secho("\n─── USDT Balance ───────────────────────────", fg="cyan")
        click.echo(f"  Wallet Balance   : {usdt.get('walletBalance')}")
        click.echo(f"  Available Balance: {usdt.get('availableBalance')}")
        click.echo(f"  Unrealised PnL   : {usdt.get('unrealizedProfit')}")
        click.echo("─────────────────────────────────────────────\n")
    else:
        click.echo("\nNo USDT asset found in account.\n")


# ── open-orders command ───────────────────────────────────────────────────────

@cli.command("open-orders")
@click.option("--symbol", default=None, help="Filter by symbol (optional)")
def open_orders(symbol: Optional[str]):
    """List open orders on Binance Futures Testnet."""
    client = _get_client()
    try:
        orders = client.get_open_orders(symbol=symbol)
    except BinanceAPIError as exc:
        click.secho(f"\n[API ERROR] {exc}\n", fg="red", err=True)
        sys.exit(1)

    if not orders:
        click.echo("\nNo open orders found.\n")
        return

    click.secho(f"\n{'─'*60}", fg="cyan")
    click.secho(f"  {'ID':<12} {'Symbol':<12} {'Side':<6} {'Type':<14} {'Qty':<10} {'Price'}", fg="cyan")
    click.secho(f"{'─'*60}", fg="cyan")
    for o in orders:
        click.echo(
            f"  {o.get('orderId',''):<12} {o.get('symbol',''):<12} "
            f"{o.get('side',''):<6} {o.get('type',''):<14} "
            f"{o.get('origQty',''):<10} {o.get('price','')}"
        )
    click.secho(f"{'─'*60}\n", fg="cyan")


if __name__ == "__main__":
    cli()
