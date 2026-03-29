"""Tests for quay CLI."""

from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from quay.cli import EXIT_ERROR
from quay.cli import EXIT_SUCCESS
from quay.cli import EXIT_USAGE
from quay.cli import main


class TestCLIExitCodes:
    """Verify exit codes are defined correctly."""

    def test_exit_codes(self):
        """Exit codes are distinct integers."""
        assert EXIT_SUCCESS == 0
        assert EXIT_ERROR == 1
        assert EXIT_USAGE == 2
        assert EXIT_SUCCESS != EXIT_ERROR


class TestCLIParsing:
    """Test CLI argument parsing without requiring Chrome."""

    def test_help_flag(self):
        """--help exits successfully."""
        with patch("sys.stdout"):
            code = main(["--help"])
        assert code == 0

    def test_empty_args(self):
        """No args prints help and exits with usage error."""
        with patch("sys.stdout"), patch("sys.stderr"):
            code = main([])
        assert code == EXIT_USAGE

    def test_invalid_command(self):
        """Invalid command exits with usage error."""
        with patch("sys.stderr"):
            code = main(["not_a_real_command"])
        assert code == EXIT_USAGE

    def test_list_command_recognized(self):
        """list command is recognized and dispatches."""
        with patch("quay.browser.Browser") as mock_cls:
            mock_instance = mock_cls.return_value
            mock_instance.list_tabs.return_value = []
            code = main(["list"])
        # May succeed (Chrome running) or fail (no Chrome) but doesn't USAGE error
        assert code in (EXIT_SUCCESS, EXIT_ERROR)

    def test_snapshot_command_recognized(self):
        """snapshot command is recognized."""
        with patch("quay.browser.Browser") as mock_cls:
            mock_instance = mock_cls.return_value
            mock_instance.list_tabs.return_value = []
            mock_instance.accessibility_tree.return_value = MagicMock()
            code = main(["snapshot"])
        assert code in (EXIT_SUCCESS, EXIT_ERROR)
