"""
Display package for Fantasy Football Challenge Tracker.

This package provides formatters for different output formats:
- Console: Human-readable tables for terminal output
- Sheets: TSV format for Google Sheets import
- Email: Mobile-friendly HTML for email reports
- JSON: Structured JSON data for further processing
- Markdown: Markdown format for GitHub, Slack, Discord, etc.

All formatters implement the BaseFormatter protocol for consistent interface.
"""

from .base import BaseFormatter, ReportContext, ReportMode
from .console import ConsoleFormatter
from .email import EmailFormatter
from .factory import create_formatter, get_available_formats
from .json import JsonFormatter
from .markdown import MarkdownFormatter
from .sheets import SheetsFormatter

__all__ = [
    "BaseFormatter",
    "ConsoleFormatter",
    "EmailFormatter",
    "JsonFormatter",
    "MarkdownFormatter",
    "SheetsFormatter",
    "ReportContext",
    "ReportMode",
    "create_formatter",
    "get_available_formats",
]
