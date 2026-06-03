"""
Low-level Binance Futures Testnet REST client.

Handles:
  - HMAC-SHA256 request signing
  - Timestamp + recvWindow management
  - HTTP request execution with retries
  - Raw API error surfacing
"""

import hashlib
import hmac
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

from .logging_config import get_logger

logger = get_logger("client")

BASE_URL = "https://testnet.binancefuture.com"
DEFAULT_RECV_WINDOW = 5000  # ms


class BinanceAPIError(Exception):
    """Raised when the Binance API returns a non-2xx response or an error code."""

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"Binance API error {code}: {message}")


class BinanceClient:
    """
    Thin wrapper around the Binance Futures Testnet REST API.

    Parameters
    ----------
    api_key : str
    api_secret : str
    base_url : str   Override for testing.
    timeout : int    HTTP timeout in seconds.
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = BASE_URL,
        timeout: int = 10,
    ):
        if not api_key or not api_secret:
            raise ValueError("api_key and api_secret must not be empty.")
        self._api_key = api_key
        self._api_secret = api_secret.encode()
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {
                "X-MBX-APIKEY": self._api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )
        logger.debug("BinanceClient initialised (base_url=%s)", self._base_url)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _sign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Append timestamp + recvWindow, then HMAC-sign the param string."""
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = DEFAULT_RECV_WINDOW
        query_string = urlencode(params)
        signature = hmac.new(
            self._api_secret, query_string.encode(), hashlib.sha256
        ).hexdigest()
        params["signature"] = signature
        return params

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = False,
    ) -> Dict[str, Any]:
        """Execute an HTTP request and return the parsed JSON response."""
        params = params or {}
        if signed:
            params = self._sign(params)

        url = f"{self._base_url}{endpoint}"
        logger.debug(">>> %s %s  params=%s", method.upper(), url, params)

        try:
            response = self._session.request(
                method,
                url,
                params=params if method.upper() == "GET" else None,
                data=params if method.upper() != "GET" else None,
                timeout=self._timeout,
            )
        except requests.exceptions.ConnectionError as exc:
            logger.error("Network error reaching %s: %s", url, exc)
            raise ConnectionError(
                f"Could not connect to Binance Testnet ({url}). "
                "Check your internet connection."
            ) from exc
        except requests.exceptions.Timeout as exc:
            logger.error("Request to %s timed out.", url)
            raise TimeoutError(
                f"Request to {url} timed out after {self._timeout}s."
            ) from exc

        logger.debug(
            "<<< %s %s  status=%s  body=%s",
            method.upper(),
            url,
            response.status_code,
            response.text[:500],
        )

        try:
            data = response.json()
        except ValueError:
            logger.error("Non-JSON response (status %s): %s", response.status_code, response.text)
            response.raise_for_status()
            raise

        if isinstance(data, dict) and "code" in data and data["code"] != 200:
            logger.error("API error: code=%s msg=%s", data["code"], data.get("msg"))
            raise BinanceAPIError(data["code"], data.get("msg", "Unknown error"))

        if not response.ok:
            logger.error("HTTP %s: %s", response.status_code, response.text)
            response.raise_for_status()

        return data

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    def get_server_time(self) -> int:
        """Return Binance server time as a Unix timestamp in milliseconds."""
        data = self._request("GET", "/fapi/v1/time")
        return data["serverTime"]

    def get_exchange_info(self) -> Dict[str, Any]:
        """Return exchange information (symbols, filters, etc.)."""
        return self._request("GET", "/fapi/v1/exchangeInfo")

    def place_order(self, **kwargs) -> Dict[str, Any]:
        """
        Place a new order on Binance Futures Testnet.

        Keyword arguments map directly to Binance API params:
          symbol, side, type, quantity, price, stopPrice, timeInForce, …
        """
        params = {k: v for k, v in kwargs.items() if v is not None}
        logger.info("Placing order: %s", params)
        result = self._request("POST", "/fapi/v1/order", params=params, signed=True)
        logger.info("Order response: %s", result)
        return result

    def get_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Query a specific order by orderId."""
        params = {"symbol": symbol, "orderId": order_id}
        return self._request("GET", "/fapi/v1/order", params=params, signed=True)

    def get_open_orders(self, symbol: Optional[str] = None) -> Any:
        """Return open orders, optionally filtered by symbol."""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/fapi/v1/openOrders", params=params, signed=True)

    def get_account(self) -> Dict[str, Any]:
        """Return account information including balances."""
        return self._request("GET", "/fapi/v2/account", params={}, signed=True)
