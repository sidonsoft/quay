#!/usr/bin/env python3
"""Install-time Python version check before delegating to setuptools."""

import sys

from setuptools import setup

# Minimum Python version required (must match requires-python in pyproject.toml)
_MIN_PYTHON = (3, 10)

if sys.version_info[:2] < _MIN_PYTHON:  # noqa: UP036
    v = sys.version_info
    print(
        f"ERROR: Python 3.10 or higher is required to install quay.\n"
        f"       You have Python {v.major}.{v.minor}.{v.micro}.\n"
        f"\n"
        f"To install with Python 3.11:\n"
        f"  python3.11 -m pip install .\n"
        f"\n"
        f"To install with Python 3.12:\n"
        f"  python3.12 -m pip install .\n"
        f"\n"
        f"To upgrade Python, visit: https://www.python.org/downloads/\n"
    )
    sys.exit(1)

setup()
