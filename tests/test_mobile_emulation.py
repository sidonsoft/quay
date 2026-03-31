"""Test mobile emulation functionality - basic verification."""
import asyncio

import pytest

from quay import Browser


@pytest.mark.asyncio
async def test_emulate_device_methods_exist():
    """Test that emulate_device and get_emulated_device methods exist."""
    browser = Browser.launch(headless=True)

    # Verify methods exist
    assert hasattr(browser, 'emulate_device'), "emulate_device method should exist"
    assert hasattr(
        browser, 'get_emulated_device'
    ), "get_emulated_device method should exist"

    await browser.aclose()


@pytest.mark.asyncio
async def test_emulate_iphone_14_exists():
    """Test that iPhone 14 device exists in descriptor."""
    from quay.browser import _DEVICES

    assert "iPhone 14" in _DEVICES, "iPhone 14 should be in device descriptors"
    assert "userAgent" in _DEVICES["iPhone 14"], "iPhone 14 should have userAgent"
    assert "viewport" in _DEVICES["iPhone 14"], "iPhone 14 should have viewport"


@pytest.mark.asyncio
async def test_emulate_device_callable():
    """Test that emulate_device can be called without error."""
    browser = Browser.launch(headless=True)
    tab = browser.goto("https://example.com")

    # Call emulate_device (should not raise)
    browser.emulate_device("iPhone 14")
    await asyncio.sleep(0.5)

    # Call get_emulated_device (should not raise)
    browser.get_emulated_device(tab=tab)
    await asyncio.sleep(0.5)

    await browser.aclose()


@pytest.mark.asyncio
async def test_all_devices_exist():
    """Test that all device descriptors exist."""
    from quay.browser import _DEVICES

    expected_devices = [
        "iPhone 14 Pro",
        "iPhone 14",
        "iPhone SE",
        "iPad Pro 12.9",
        "iPad Air",
        "Samsung Galaxy S21",
        "Samsung Galaxy S20",
        "Google Pixel 7",
        "Google Pixel 6",
        "Motorola Moto G4",
    ]

    for device in expected_devices:
        assert device in _DEVICES, f"{device} should be in device descriptors"

    assert len(_DEVICES) == 10, "Should have exactly 10 device descriptors"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
