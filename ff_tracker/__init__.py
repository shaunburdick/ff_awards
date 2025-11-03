"""
Fantasy Football Challenge Tracker

A modern, type-safe CLI tool for tracking fantasy football challenges across
multiple ESPN leagues. Supports various output formats and both public and
private leagues.

Usage:
    python -m ff_tracker LEAGUE_ID [--year YEAR] [--private] [--format FORMAT]

Example:
    python -m ff_tracker 123456 --year 2024 --format console
"""

from importlib.metadata import version

from .main import main

__version__ = version("ff-awards")
__author__ = "Shaun Burdick"

__all__ = ["main"]
