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

from .main import main

__version__ = "2.0.0"
__author__ = "Shaun Burdick"

__all__ = ["main"]
