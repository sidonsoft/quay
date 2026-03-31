"""Test stealth script injection timing fix."""

import asyncio
import os

import pytest

from quay import Browser


@pytest.mark.skipif(
    os.environ.get("QUAY_SKIP_CHROME") == "1",
    reason="requires Chrome running",
)
@pytest.mark.asyncio
async def test_stealth_timing():
    """Verify stealth scripts are injected before navigation starts."""
    browser = Browser.launch(
        headless=True,
        stealth=True,
        block_trackers=True,
    )

    try:
        # Test 1: Check stealth injection on new_tab()
        print("Test 1: Testing new_tab() with stealth mode...")
        tab = browser.new_tab("https://bot.sannysoft.com/")

        # Wait for page to load
        await asyncio.sleep(3)

        # Check stealth signals - simpler approach
        result = await browser.evaluate("navigator.webdriver", tab=tab)

        print(f"navigator.webdriver: {result}")

        # Verify webdriver is hidden
        msg = f"navigator.webdriver should be None/False, got {result}"
        assert result is None or not result, msg

        print("Test 1 PASSED: navigator.webdriver hidden on new_tab()")

        # Test 2: Check stealth injection on goto()
        print("\nTest 2: Testing goto() with stealth mode...")
        tab2 = browser.goto("https://bot.sannysoft.com/")

        await asyncio.sleep(3)

        result2 = await browser.evaluate("navigator.webdriver", tab=tab2)

        print(f"navigator.webdriver: {result2}")

        msg2 = f"navigator.webdriver should be None/False, got {result2}"
        assert result2 is None or not result2, msg2

        print("Test 2 PASSED: navigator.webdriver hidden on goto()")

        print("\nAll stealth timing tests PASSED!")

    finally:
        await browser.aclose()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
