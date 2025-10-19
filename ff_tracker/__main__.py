"""
Allow the package to be run as a module.

This enables running the CLI with:
    python -m ff_tracker
"""

from .main import main

if __name__ == "__main__":
    import sys
    sys.exit(main())
