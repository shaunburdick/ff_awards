"""
Formatter factory for creating formatter instances.

This module centralizes formatter creation logic to eliminate duplication
between main.py and championship.py.
"""

from __future__ import annotations

from .base import BaseFormatter
from .console import ConsoleFormatter
from .email import EmailFormatter
from .json import JsonFormatter
from .markdown import MarkdownFormatter
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
