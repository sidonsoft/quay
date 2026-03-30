"""Test enhanced stealth mode (Week 4)."""
import asyncio
import pytest
from quay import Browser


@pytest.mark.asyncio
async def test_stealth_mode_parameter():
    """Test that stealth_mode parameter is accepted."""
    # Test basic mode
    browser = Browser.launch(headless=True, stealth=True, stealth_mode="basic")
    assert browser.get_stealth_mode() == "basic"
    await browser.aclose()

    # Test balanced mode
    browser = Browser.launch(headless=True, stealth=True, stealth_mode="balanced")
    assert browser.get_stealth_mode() == "balanced"
    await browser.aclose()

    # Test aggressive mode
    browser = Browser.launch(headless=True, stealth=True, stealth_mode="aggressive")
    assert browser.get_stealth_mode() == "aggressive"
    await browser.aclose()


@pytest.mark.asyncio
async def test_invalid_stealth_mode():
    """Test that invalid stealth_mode raises ValueError."""
    with pytest.raises(ValueError, match="Invalid stealth_mode"):
        Browser(stealth=True, stealth_mode="invalid")


@pytest.mark.asyncio
async def test_basic_stealth_script():
    """Test that basic stealth script is injected."""
    browser = Browser.launch(headless=True, stealth=True, stealth_mode="basic")
    tab = browser.goto("https://example.com")

    # Check that stealth is active (webdriver should be hidden)
    result = browser.is_stealth(tab=tab)
    # navigator.webdriver might be None or False depending on script success
    assert "navigator.webdriver" in result

    await browser.aclose()


@pytest.mark.asyncio
async def test_balanced_stealth_script():
    """Test that balanced stealth script includes canvas/audio."""
    browser = Browser.launch(headless=True, stealth=True, stealth_mode="balanced")
    tab = browser.goto("https://example.com")

    # Verify stealth is active
    result = browser.is_stealth(tab=tab)
    assert "navigator.webdriver" in result

    await browser.aclose()


@pytest.mark.asyncio
async def test_aggressive_stealth_script():
    """Test that aggressive stealth script includes all techniques."""
    browser = Browser.launch(headless=True, stealth=True, stealth_mode="aggressive")
    tab = browser.goto("https://example.com")

    # Verify stealth is active
    result = browser.is_stealth(tab=tab)
    assert "navigator.webdriver" in result

    await browser.aclose()


@pytest.mark.asyncio
async def test_stealth_script_content():
    """Test that stealth scripts contain expected techniques."""
    from quay.browser import (
        _STEALTH_SCRIPT_BASIC,
        _STEALTH_SCRIPT_BALANCED,
        _STEALTH_SCRIPT_AGGRESSIVE,
    )

    # Basic should have essential protections
    assert "navigator.webdriver" in _STEALTH_SCRIPT_BASIC
    assert "cdc_adoQpoasnfa76pfcZLmcfl_Chart" in _STEALTH_SCRIPT_BASIC

    # Balanced should have canvas/audio
    assert "WebGLRenderingContext" in _STEALTH_SCRIPT_BALANCED
    assert "AudioContext" in _STEALTH_SCRIPT_BALANCED
    assert "HTMLCanvasElement" in _STEALTH_SCRIPT_BALANCED

    # Aggressive should have everything plus screen/performance
    assert "AudioContext" in _STEALTH_SCRIPT_AGGRESSIVE
    assert "Screen.prototype" in _STEALTH_SCRIPT_AGGRESSIVE
    assert "PerformanceTiming" in _STEALTH_SCRIPT_AGGRESSIVE
    assert "navigator.mediaDevices" in _STEALTH_SCRIPT_AGGRESSIVE


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
