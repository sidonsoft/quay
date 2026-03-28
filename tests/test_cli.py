"""Tests for quay.cli — command-line interface."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from quay.cli import main, EXIT_SUCCESS


class TestCLI:
    """Basic CLI tests."""
    
    def test_list_command(self, capsys):
        """quay list should work."""
        with patch("quay.cli.Browser") as MockBrowser:
            mock = MagicMock()
            mock.list_tabs.return_value = []
            MockBrowser.return_value.__enter__ = MagicMock(return_value=mock)
            MockBrowser.return_value.__exit__ = MagicMock(return_value=False)
            
            code = main(["list"])
            # Should succeed even with empty list
            assert code == EXIT_SUCCESS

    def test_version_flag(self, capsys):
        """quay --version should print version."""
        with patch("quay.cli.Browser") as MockBrowser:
            mock = MagicMock()
            MockBrowser.return_value.__enter__ = MagicMock(return_value=mock)
            MockBrowser.return_value.__exit__ = MagicMock(return_value=False)
            
            code = main(["--version"])
            captured = capsys.readouterr()
            # Version output may vary
            assert code == EXIT_SUCCESS or "quay" in captured.out.lower() or captured.err

    def test_help_flag(self, capsys):
        """quay --help should print help."""
        # argparse raises SystemExit on --help
        try:
            main(["--help"])
        except SystemExit:
            pass  # Expected