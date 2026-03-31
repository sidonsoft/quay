"""Test persistent profile functionality."""
import asyncio
import os
import tempfile

import pytest

from quay import Browser


@pytest.mark.asyncio
async def test_persistent_profile_basic():
    """Test that profile_path parameter is accepted and stored."""
    with tempfile.TemporaryDirectory() as tmpdir:
        browser = Browser(profile_path=tmpdir)
        assert browser._profile_path == tmpdir
        await browser.aclose()


@pytest.mark.asyncio
async def test_persistent_profile_launch():
    """Test that Browser.launch() accepts profile_path parameter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        browser = Browser.launch(
            headless=True,
            profile_path=tmpdir,
        )
        assert browser._profile_path == tmpdir
        await browser.aclose()


@pytest.mark.asyncio
async def test_persistent_profile_persistence():
    """Test that profile_path parameter is passed correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Session 1: Create browser with profile
        browser1 = Browser.launch(headless=True, profile_path=tmpdir)
        assert browser1._profile_path == tmpdir
        await browser1.aclose()

        # Session 2: Reuse same profile
        browser2 = Browser.launch(headless=True, profile_path=tmpdir)
        assert browser2._profile_path == tmpdir
        await browser2.aclose()

        # Verify directory was created
        assert os.path.exists(tmpdir), "Profile directory should be created"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
