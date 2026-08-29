"""Deprecated shim. Import telegram_ads_mcp.server instead."""

from telegram_ads_mcp.server import *  # noqa: F403
from telegram_ads_mcp.server import main, mcp

__all__ = ["main", "mcp"]
