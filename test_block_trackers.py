#!/usr/bin/env python3
"""Test block_trackers feature."""

from quay import Browser
from quay.browser import _BLOCKLIST


def test_blocklist():
    print(f"Blocklist: {len(_BLOCKLIST)} domains")
    print("Domains:", _BLOCKLIST)


def test_browser():
    b = Browser(block_trackers=True)
    print(f"block_trackers={b._block_trackers}")
    b.goto("https://example.com")
    print(f"title={b.current_tab.title}")
    b.close()
    print("OK")


if __name__ == "__main__":
    test_blocklist()
    print()
    test_browser()
