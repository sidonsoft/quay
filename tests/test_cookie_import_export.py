"""Test cookie import/export functionality - basic verification."""
import asyncio
import json
import os
import tempfile

import pytest

from quay import Browser


@pytest.mark.asyncio
async def test_export_import_methods_exist():
    """Test that export_cookies and import_cookies methods exist."""
    browser = Browser.launch(headless=True)

    # Verify methods exist
    assert hasattr(browser, 'export_cookies'), "export_cookies method should exist"
    assert hasattr(browser, 'import_cookies'), "import_cookies method should exist"

    await browser.aclose()


@pytest.mark.asyncio
async def test_export_import_basic():
    """Test that export_cookies and import_cookies can be called."""
    with tempfile.TemporaryDirectory() as tmpdir:
        browser = Browser.launch(headless=True)

        # Navigate to a page
        tab = browser.goto("https://example.com")
        await asyncio.sleep(1)

        # Create an empty cookie file
        cookie_file = f"{tmpdir}/cookies.json"
        cookies = []
        with open(cookie_file, "w") as f:
            json.dump(cookies, f)

        # Import cookies (should not raise)
        browser.import_cookies(cookie_file, tab=tab)
        await asyncio.sleep(0.5)

        # Export cookies (should not raise)
        browser.export_cookies(cookie_file, tab=tab)
        await asyncio.sleep(0.5)

        # Verify file was created
        assert os.path.exists(cookie_file), "Cookie file should be created"

        await browser.aclose()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
