"""
Shared CLI utilities for Fantasy Football Challenge Tracker.

This module provides common functions used by both ff-tracker and ff-championship
CLI scripts to avoid code duplication.
"""

from __future__ import annotations

import logging


def parse_league_ids_from_arg(league_id_arg: str) -> list[int]:
    """
    Parse league IDs from command line argument.

    Args:
        league_id_arg: Single ID or comma-separated IDs (e.g., "123456" or "123456,789012,345678")

    Returns:
        List of league IDs as integers

    Raises:
        ValueError: If league IDs are invalid or empty

    Examples:
        >>> parse_league_ids_from_arg("123456")
        [123456]
        >>> parse_league_ids_from_arg("123456,789012,345678")
        [123456, 789012, 345678]
        >>> parse_league_ids_from_arg("123, 456, 789")  # Handles spaces
        [123, 456, 789]
    """
    try:
        league_ids = [int(id_str.strip()) for id_str in league_id_arg.split(",") if id_str.strip()]
        if not league_ids:
            raise ValueError("No valid league IDs found")
        return league_ids
    except ValueError as e:
        raise ValueError(
            f"Error parsing league IDs: {e}. Format should be: 123456 or 123456,789012,345678"
        ) from e


def parse_format_args(args_list: list[str] | None) -> dict[str, dict[str, str]]:
    """
    Parse format arguments into nested dictionary structure.

    Supports two syntaxes:
    - Global: "key=value" -> {"_global": {"key": "value"}}
    - Formatter-specific: "formatter.key=value" -> {"formatter": {"key": "value"}}

    Global args apply to all formatters. Formatter-specific args override globals.

    Args:
        args_list: List of format argument strings from CLI

    Returns:
        Nested dict with "_global" key and formatter-specific keys

    Raises:
        ValueError: If argument format is invalid

    Examples:
        >>> parse_format_args(["note=Test", "email.accent_color=#ff0000"])
        {"_global": {"note": "Test"}, "email": {"accent_color": "#ff0000"}}
    """
    if not args_list:
        return {}

    result: dict[str, dict[str, str]] = {"_global": {}}

    for arg in args_list:
        if "=" not in arg:
            raise ValueError(
                f"Invalid format argument: '{arg}'. "
                f"Must be in format: key=value or formatter.key=value"
            )

        key, value = arg.split("=", 1)
        key = key.strip()
        value = value.strip()

        if not key:
            raise ValueError(f"Empty key in format argument: '{arg}'")

        # Check if formatter-specific (contains dot)
        if "." in key:
            parts = key.split(".", 1)
            if len(parts) != 2 or not parts[0] or not parts[1]:
                raise ValueError(
                    f"Invalid formatter-specific argument: '{arg}'. Must be: formatter.key=value"
                )

            formatter, arg_key = parts
            if formatter not in result:
                result[formatter] = {}
            result[formatter][arg_key] = value
        else:
            # Global argument
            result["_global"][key] = value

    return result


def get_formatter_args(
    format_name: str, format_args_dict: dict[str, dict[str, str]]
) -> dict[str, str]:
    """
    Get merged arguments for a specific formatter.

    Merges global args with formatter-specific args, with formatter-specific
    taking precedence.

    Args:
        format_name: Name of the formatter (e.g., "email", "json")
        format_args_dict: Parsed format arguments dict

    Returns:
        Merged dictionary of arguments for this formatter
    """
    merged_args = dict(format_args_dict.get("_global", {}))
    merged_args.update(format_args_dict.get(format_name, {}))
    return merged_args


def setup_logging(verbose: int = 0) -> None:
    """
    Configure logging based on verbosity level.

    Unified logging configuration for all CLI scripts. Supports both
    integer verbosity levels (-v, -vv) and boolean verbose flags.

    Args:
        verbose: Verbosity level:
            - 0: WARNING only (quiet mode)
            - 1: INFO level (normal verbosity with -v)
            - 2+: DEBUG level (maximum verbosity with -vv)

    Examples:
        >>> setup_logging(0)  # Quiet - warnings only
        >>> setup_logging(1)  # Normal - info messages
        >>> setup_logging(2)  # Verbose - debug messages
    """
    if verbose == 0:
        level = logging.WARNING
    elif verbose == 1:
        level = logging.INFO
    else:  # verbose >= 2
        level = logging.DEBUG

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Suppress noisy third-party loggers unless in DEBUG mode
    if level > logging.DEBUG:
        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("espn_api").setLevel(logging.WARNING)
