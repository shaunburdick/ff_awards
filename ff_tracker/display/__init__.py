"""
Display package for Fantasy Football Challenge Tracker.

This package provides formatters for different output formats:
- Console: Human-readable tables for terminal output
- Sheets: TSV format for Google Sheets import
- Email: Mobile-friendly HTML for email reports

All formatters implement the BaseFormatter protocol for consistent interface.
"""

from .base import BaseFormatter
from .console import ConsoleFormatter
from .email import EmailFormatter
from .sheets import SheetsFormatter

__all__ = [
    'BaseFormatter',
    'ConsoleFormatter',
    'EmailFormatter',
    'SheetsFormatter',
]
