"""
CLI wrapper for quay.

Usage:
    quay list              List all tabs
    quay new <url>         Open new tab
    quay snapshot          Get accessibility tree
    quay screenshot [path] Take screenshot
    quay html              Get page HTML
    quay eval '<js>'       Execute JavaScript
    quay click 'text'      Click by text
    quay navigate <url>    Navigate tab
    quay close [id]        Close tabs
    quay version           Show Chrome version
    quay run-evals         Run evaluation suite
"""

from __future__ import annotations

import argparse
import sys

from .browser import Browser

# Exit codes
EXIT_SUCCESS = 0
EXIT_ERROR = 1  # Runtime error
EXIT_USAGE = 2  # Invalid arguments
EXIT_INTERRUPT = 130


def print_error(message: str) -> None:
    """Print error message to stderr."""
    print(f"Error: {message}", file=sys.stderr)


def cmd_list(args: argparse.Namespace) -> int:
    """List all tabs."""
    try:
        browser = Browser(host=args.host, port=args.port)
        tabs = browser.list_tabs()
        for t in tabs:
            print(f"  {t.id[:12]}  {t.title[:30]:30}  {t.url[:60]}")
        return EXIT_SUCCESS
    except Exception as e:
        print_error(str(e))
        return EXIT_ERROR


def cmd_new(args: argparse.Namespace) -> int:
    """Open new tab."""
    try:
        browser = Browser(host=args.host, port=args.port)
        url = args.url
        tab = browser.new_tab(url)
        print(f"✓ Opened: {tab.url}")
        return EXIT_SUCCESS
    except Exception as e:
        print_error(str(e))
        return EXIT_ERROR


def cmd_snapshot(args: argparse.Namespace) -> int:
    """Get accessibility tree snapshot."""
    try:
        browser = Browser(host=args.host, port=args.port)
        tree = browser.accessibility_tree()
        print(tree.to_tree_str())
        return EXIT_SUCCESS
    except Exception as e:
        print_error(str(e))
        return EXIT_ERROR


def cmd_screenshot(args: argparse.Namespace) -> int:
    """Take screenshot."""
    path = args.path
    try:
        browser = Browser(host=args.host, port=args.port)
        browser.screenshot(path)
        print(f"✓ Saved: {path}")
        return EXIT_SUCCESS
    except Exception as e:
        print_error(str(e))
        return EXIT_ERROR


def cmd_html(args: argparse.Namespace) -> int:
    """Get page HTML."""
    try:
        browser = Browser(host=args.host, port=args.port)
        html = browser.get_html()
        print(html)
        return EXIT_SUCCESS
    except Exception as e:
        print_error(str(e))
        return EXIT_ERROR


def cmd_eval(args: argparse.Namespace) -> int:
    """Execute JavaScript."""
    try:
        browser = Browser(host=args.host, port=args.port)
        result = browser.evaluate(" ".join(args.script))
        print(result)
        return EXIT_SUCCESS
    except Exception as e:
        print_error(str(e))
        return EXIT_ERROR


def cmd_click(args: argparse.Namespace) -> int:
    """Click element by text."""
    try:
        browser = Browser(host=args.host, port=args.port)
        text = " ".join(args.text)
        result = browser.click_by_text(text)
        print(f"✓ Clicked: {result}")
        return EXIT_SUCCESS
    except Exception as e:
        print_error(str(e))
        return EXIT_ERROR


def cmd_navigate(args: argparse.Namespace) -> int:
    """Navigate current tab."""
    try:
        browser = Browser(host=args.host, port=args.port)
        url = args.url
        if not browser.current_tab:
            tabs = browser.list_tabs()
            if tabs:
                browser.current_tab = tabs[0]
        browser.navigate(url)
        print(f"✓ Navigated to: {url}")
        return EXIT_SUCCESS
    except Exception as e:
        print_error(str(e))
        return EXIT_ERROR


def cmd_close(args: argparse.Namespace) -> int:
    """Close tabs."""
    try:
        browser = Browser(host=args.host, port=args.port)
        if args.ids:
            for tab_id in args.ids:
                browser.close_tab(tab_id)
                print(f"✓ Closed: {tab_id}")
        else:
            # Close all non-chrome tabs
            for t in browser.list_tabs():
                if not t.url.startswith("chrome://"):
                    browser.close_tab(t.id)
                    print(f"✓ Closed: {t.url[:40]}")
        return EXIT_SUCCESS
    except Exception as e:
        print_error(str(e))
        return EXIT_ERROR


def cmd_version(args: argparse.Namespace) -> int:
    """Show Chrome version."""
    try:
        browser = Browser(host=args.host, port=args.port)
        info = browser.get_version()
        print(f"Browser: {info.browser}")
        print(f"Protocol: {info.protocol_version}")
        print(f"User-Agent: {info.user_agent[:60]}...")
        return EXIT_SUCCESS
    except Exception as e:
        print_error(str(e))
        return EXIT_ERROR


def cmd_run_evals(args: argparse.Namespace) -> int:
    """Run evaluation suite."""
    from .evals import run_evals

    try:
        browser = Browser(host=args.host, port=args.port)
        # Verify connection
        browser.get_version()

        report = run_evals(
            suites=args.suite or None, verbose=not args.quiet, report_path=args.report
        )

        if not args.quiet:
            print()
            print(report.summary())

        # Exit code based on pass rate
        return EXIT_SUCCESS if report.pass_rate == 1.0 else EXIT_ERROR

    except Exception as e:
        print_error(f"Eval failed: {e}")
        return EXIT_ERROR


COMMANDS = {
    "list": cmd_list,
    "new": cmd_new,
    "snapshot": cmd_snapshot,
    "screenshot": cmd_screenshot,
    "html": cmd_html,
    "eval": cmd_eval,
    "click": cmd_click,
    "navigate": cmd_navigate,
    "close": cmd_close,
    "version": cmd_version,
    "run-evals": cmd_run_evals,
}


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Browser Hybrid - Chrome DevTools with accessibility semantics"
    )
    # Global options
    parser.add_argument("--host", default="localhost", help="Chrome DevTools host")
    parser.add_argument("--port", type=int, default=9222, help="Chrome DevTools port")

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # list
    subparsers.add_parser("list", help="List all tabs")

    # new
    new_parser = subparsers.add_parser("new", help="Open new tab")
    new_parser.add_argument("url", help="URL to open")

    # snapshot
    subparsers.add_parser("snapshot", help="Get accessibility tree snapshot")

    # screenshot
    ss_parser = subparsers.add_parser("screenshot", help="Take screenshot")
    ss_parser.add_argument("path", nargs="?", default="/tmp/screenshot.png", help="Path to save")

    # html
    subparsers.add_parser("html", help="Get page HTML")

    # eval
    eval_parser = subparsers.add_parser("eval", help="Execute JavaScript")
    eval_parser.add_argument("script", nargs="+", help="JavaScript code")

    # click
    click_parser = subparsers.add_parser("click", help="Click element by text")
    click_parser.add_argument("text", nargs="+", help="Visible text to click")

    # navigate
    nav_parser = subparsers.add_parser("navigate", help="Navigate current tab")
    nav_parser.add_argument("url", help="URL to navigate to")

    # close
    close_parser = subparsers.add_parser("close", help="Close tabs")
    close_parser.add_argument("ids", nargs="*", help="Tab IDs to close")

    # version
    subparsers.add_parser("version", help="Show Chrome version")

    # run-evals
    evals_parser = subparsers.add_parser("run-evals", help="Run evaluation suite")
    evals_parser.add_argument("--suite", action="append", help="Run specific suite")
    evals_parser.add_argument("--report", help="Save JSON report")
    evals_parser.add_argument("--quiet", action="store_true", help="Quiet output")

    if argv is None:
        argv = sys.argv[1:]

    if not argv:
        parser.print_help()
        return EXIT_USAGE

    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        # argparse raises SystemExit on --help or error
        return e.code if isinstance(e.code, int) else EXIT_USAGE

    if not args.command:
        parser.print_help()
        return EXIT_USAGE

    # Dispatch
    cmd_func = COMMANDS.get(args.command)
    if not cmd_func:
        print_error(f"Unknown command: {args.command}")
        return EXIT_USAGE

    try:
        return cmd_func(args)
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        return EXIT_INTERRUPT
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
