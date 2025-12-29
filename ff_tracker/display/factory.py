"""
Formatter factory for creating formatter instances.

This module centralizes formatter creation logic to eliminate duplication
between main.py, championship.py, and season_recap.py.
"""

from __future__ import annotations

from .base import BaseFormatter
from .console import ConsoleFormatter
from .email import EmailFormatter
from .json import JsonFormatter
from .markdown import MarkdownFormatter
from .season_recap_console import SeasonRecapConsoleFormatter
from .season_recap_email import SeasonRecapEmailFormatter
from .season_recap_json import SeasonRecapJsonFormatter
from .season_recap_markdown import SeasonRecapMarkdownFormatter
from .season_recap_sheets import SeasonRecapSheetsFormatter
from .sheets import SheetsFormatter


def create_formatter(
    format_name: str,
    year: int,
    format_args: dict[str, str] | None = None,
) -> BaseFormatter:
    """
    Create a formatter instance by name.

    This factory function centralizes formatter creation logic, ensuring
    consistent instantiation across the application.

    Args:
        format_name: Name of the formatter (console, sheets, email, json, markdown)
        year: Fantasy season year for display
        format_args: Optional dict of formatter-specific arguments

    Returns:
        Configured formatter instance

    Raises:
        ValueError: If format name is unknown

    Examples:
        >>> formatter = create_formatter("console", 2024)
        >>> formatter = create_formatter("email", 2024, {"accent_color": "#007bff"})
    """
    formatters = {
        "console": ConsoleFormatter,
        "sheets": SheetsFormatter,
        "email": EmailFormatter,
        "json": JsonFormatter,
        "markdown": MarkdownFormatter,
    }

    formatter_class = formatters.get(format_name)
    if not formatter_class:
        valid_formats = ", ".join(formatters.keys())
        raise ValueError(f"Unknown format: {format_name}. Valid formats: {valid_formats}")

    return formatter_class(year, format_args)


def get_available_formats() -> list[str]:
    """
    Get list of available formatter names.

    Returns:
        List of valid formatter names

    Examples:
        >>> formats = get_available_formats()
        >>> print(formats)
        ['console', 'sheets', 'email', 'json', 'markdown']
    """
    return ["console", "sheets", "email", "json", "markdown"]


def create_season_recap_formatter(
    format_name: str,
    year: int,
    format_args: dict[str, str] | None = None,
) -> BaseFormatter:
    """
    Create a season recap formatter instance by name.

    Season recap formatters have a different interface than weekly formatters,
    so they need a separate factory method.

    Args:
        format_name: Name of the formatter (console, sheets, email, json, markdown)
        year: Fantasy season year for display
        format_args: Optional dict of formatter-specific arguments

    Returns:
        Configured season recap formatter instance

    Raises:
        ValueError: If format name is unknown

    Examples:
        >>> formatter = create_season_recap_formatter("console", 2024)
        >>> formatter = create_season_recap_formatter("email", 2024, {"accent_color": "#007bff"})
    """
    formatters = {
        "console": SeasonRecapConsoleFormatter,
        "json": SeasonRecapJsonFormatter,
        "sheets": SeasonRecapSheetsFormatter,
        "markdown": SeasonRecapMarkdownFormatter,
        "email": SeasonRecapEmailFormatter,
    }

    formatter_class = formatters.get(format_name)
    if not formatter_class:
        valid_formats = ", ".join(formatters.keys())
        raise ValueError(
            f"Unknown season recap format: {format_name}. Valid formats: {valid_formats}"
        )

    return formatter_class(year, format_args)
