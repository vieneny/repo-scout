#!/usr/bin/env python3
"""Portable entrypoint; Python 3.10+, no third-party packages."""
from scout.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
