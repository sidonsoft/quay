"""
Eval system for browser-hybrid.

Code-based evaluations for deterministic testing of browser automation.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from quay import Browser
from quay.errors import (
    BrowserError,
    ConnectionError,
    TimeoutError,
)


@dataclass
class EvalCase:
    """A single test case for eval."""

    name: str
    suite: str
    input: dict[str, Any]
    expected: dict[str, Any]
    human_judgment: dict[str, Any] | None = None


@dataclass
class EvalResult:
    """Result of running a single eval case."""

    case: EvalCase
    passed: bool
    actual: Any = None
    error: str | None = None
    duration_ms: float = 0.0
    critique: str | None = None


@dataclass
class EvalReport:
    """Report from running all evals."""

    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    results: list[EvalResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def pass_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.passed_count / self.total

    def by_suite(self) -> dict[str, list[EvalResult]]:
        """Group results by suite."""
        suites: dict[str, list[EvalResult]] = {}
        for r in self.results:
            suite = r.case.suite
            if suite not in suites:
                suites[suite] = []
            suites[suite].append(r)
        return suites

    def summary(self) -> str:
        """Generate summary string."""
        lines = ["=== Eval Results ==="]

        for suite, results in sorted(self.by_suite().items()):
            passed = sum(1 for r in results if r.passed)
            total = len(results)
            status = "PASSED" if passed == total else f"{passed}/{total} PASSED"
            lines.append(f"{suite}: {status}")

        lines.append("")
        lines.append(f"Total: {self.passed_count}/{self.total} PASSED ({self.pass_rate:.1%})")

        # Add failures if any
        if self.failed_count > 0:
            lines.append("")
            lines.append("Failed cases:")
            for r in self.results:
                if not r.passed:
                    lines.append(f"  - {r.case.suite}/{r.case.name}: {r.error}")

        return "\n".join(lines)

    def to_json(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "timestamp": self.timestamp,
            "total": self.total,
            "passed": self.passed_count,
            "failed": self.failed_count,
            "pass_rate": self.pass_rate,
            "results": [
                {
                    "suite": r.case.suite,
                    "name": r.case.name,
                    "passed": r.passed,
                    "actual": r.actual,
                    "expected": r.case.expected,
                    "error": r.error,
                    "duration_ms": r.duration_ms,
                }
                for r in self.results
            ],
        }


class EvalRunner:
    """
    Runner for browser-hybrid evals.

    Usage:
        runner = EvalRunner()
        report = runner.run()
        print(report.summary())

    Or run specific suites:
        report = runner.run(suites=["connection", "navigation"])
    """

    def __init__(
        self,
        evals_dir: str | Path | None = None,
        browser: Browser | None = None,
    ):
        """
        Initialize eval runner.

        Args:
            evals_dir: Directory containing eval YAML files
            browser: Browser instance (created if not provided)
        """
        if evals_dir is None:
            # Default: look for evals/ in project root
            # __file__ is in src/quay/evals.py
            # Project root is two levels up
            project_root = Path(__file__).parent.parent.parent
            evals_dir = project_root / "evals"
        self.evals_dir = Path(evals_dir)
        self._browser = browser
        self._owns_browser = browser is None

    @property
    def browser(self) -> Browser:
        """Get or create browser instance."""
        if self._browser is None:
            self._browser = Browser()
        return self._browser

    def load_cases(self, suites: list[str] | None = None) -> list[EvalCase]:
        """
        Load eval cases from YAML files.

        Args:
            suites: Specific suites to load (None = all)

        Returns:
            List of EvalCase objects
        """
        cases: list[EvalCase] = []

        if not self.evals_dir.exists():
            return cases

        for yaml_file in self.evals_dir.glob("*.yaml"):
            suite_name = yaml_file.stem

            if suites and suite_name not in suites:
                continue

            with open(yaml_file) as f:
                data = yaml.safe_load(f)

            if not data or "cases" not in data:
                continue

            for case_data in data["cases"]:
                case = EvalCase(
                    name=case_data["name"],
                    suite=suite_name,
                    input=case_data.get("input", {}),
                    expected=case_data.get("expected", {}),
                    human_judgment=case_data.get("human_judgment"),
                )
                cases.append(case)

        return cases

    def run(self, suites: list[str] | None = None, verbose: bool = False) -> EvalReport:
        """
        Run eval cases and generate report.

        Args:
            suites: Specific suites to run (None = all)
            verbose: Print progress

        Returns:
            EvalReport with results
        """
        cases = self.load_cases(suites)
        report = EvalReport()

        try:
            for case in cases:
                if verbose:
                    print(f"Running {case.suite}/{case.name}...", end=" ", flush=True)

                result = self._run_case(case)
                report.results.append(result)

                if verbose:
                    status = "PASSED" if result.passed else "FAILED"
                    print(status)
        finally:
            if self._owns_browser and self._browser:
                try:
                    self._browser.close()
                except Exception:
                    pass

        return report

    def _run_case(self, case: EvalCase) -> EvalResult:
        """Run a single eval case."""
        start_time = time.time()
        result = EvalResult(case=case, passed=False)

        try:
            # Execute based on suite
            actual = self._execute_case(case)
            result.actual = actual

            # Validate against expected
            passed, error = self._validate(actual, case.expected)
            result.passed = passed
            result.error = error

        except ConnectionError as e:
            result.error = f"ConnectionError: {e}"
            result.actual = {"error": "ConnectionError", "message": str(e)}
        except TimeoutError as e:
            result.error = f"TimeoutError: {e}"
            result.actual = {"error": "TimeoutError", "message": str(e)}
        except BrowserError as e:
            result.error = f"BrowserError: {e}"
            result.actual = {"error": "BrowserError", "message": str(e)}
        except Exception as e:
            result.error = f"Unexpected error: {e}"
            result.actual = {"error": type(e).__name__, "message": str(e)}

        result.duration_ms = (time.time() - start_time) * 1000
        return result

    def _execute_case(self, case: EvalCase) -> Any:
        """Execute eval case and return actual result."""
        suite = case.suite
        inputs = case.input

        if suite == "connection":
            return self._execute_connection(inputs)
        elif suite == "navigation":
            return self._execute_navigation(inputs)
        elif suite == "elements":
            return self._execute_elements(inputs)
        elif suite == "javascript":
            return self._execute_javascript(inputs)
        elif suite == "accessibility":
            return self._execute_accessibility(inputs)
        elif suite == "errors":
            return self._execute_errors(inputs)
        else:
            raise ValueError(f"Unknown suite: {suite}")

    def _execute_connection(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Execute connection eval."""
        operation = inputs.get("operation", "connect")

        if operation == "get_version":
            info = self.browser.get_version()
            return {
                "browser": info.browser,
                "protocol_version": info.protocol_version,
            }
        else:
            # Default: just connect
            connected = self.browser.is_connected()
            return {"connected": connected}

    def _execute_navigation(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Execute navigation eval."""
        url = inputs.get("url", "about:blank")
        timeout = inputs.get("timeout", 10.0)

        tab = self.browser.goto(url, timeout=timeout)

        result = {
            "url": tab.url,
            "title": self.browser.evaluate("document.title"),
        }

        if inputs.get("close", True):
            self.browser.close_tab(tab.id)

        return result

    def _execute_elements(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Execute element finding eval."""
        page = inputs.get("page", "about:blank")
        find_text = inputs.get("find_text")
        find_role = inputs.get("find_role")

        tab = self.browser.goto(page, timeout=10.0)
        tree = self.browser.accessibility_tree()

        result: dict[str, Any] = {"url": page}

        if find_text:
            # Use find_by_name for text matching
            found = tree.find_by_name(find_text)
            result["found"] = len(found) > 0
            result["count"] = len(found)
            if found:
                result["element_role"] = found[0].role

        if find_role:
            elements = tree.find_by_role(find_role)
            result["count"] = len(elements)
            result["found"] = len(elements) > 0
            if elements:
                result["element_role"] = elements[0].role

        if inputs.get("close", True):
            self.browser.close_tab(tab.id)

        return result

    def _execute_javascript(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Execute JavaScript eval."""
        script = inputs.get("script", "undefined")
        page = inputs.get("page")

        if page:
            tab = self.browser.goto(page, timeout=10.0)

        result = self.browser.evaluate(script)

        if page and inputs.get("close", True):
            self.browser.close_tab(tab.id)

        return {"result": result}

    def _execute_accessibility(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Execute accessibility tree eval."""
        page = inputs.get("page", "about:blank")
        find_role = inputs.get("find_role")

        tab = self.browser.goto(page, timeout=10.0)
        tree = self.browser.accessibility_tree()

        result: dict[str, Any] = {
            "root_role": tree.role,
        }

        if find_role:
            elements = tree.find_by_role(find_role)
            result["count"] = len(elements)
            result["found"] = len(elements) > 0

        if inputs.get("close", True):
            self.browser.close_tab(tab.id)

        return result

    def _execute_errors(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Execute error handling eval."""
        # Most error cases need special handling
        # For now, just return the inputs for validation
        return {"inputs": inputs}

    def _validate(self, actual: Any, expected: dict[str, Any]) -> tuple[bool, str | None]:
        """
        Validate actual against expected.

        Returns:
            (passed, error_message)
        """
        # Check for error expectation
        if "error" in expected:
            if isinstance(actual, dict) and actual.get("error") == expected["error"]:
                # Check context if specified
                # Note: Would need exception context to fully validate
                # For now, pass if error type matches
                return True, None
            else:
                return False, f"Expected error {expected['error']}, got {actual}"

        if "browser_contains" in expected:
            browser_str = actual.get("browser", "") if isinstance(actual, dict) else ""
            if expected["browser_contains"] in browser_str:
                return True, None
            expected_str = expected["browser_contains"]
            return False, f"Expected '{expected_str}' in browser, got {browser_str}"

        # Validate URL contains
        if "url_contains" in expected:
            url = actual.get("url", "") if isinstance(actual, dict) else ""
            if expected["url_contains"] in url:
                return True, None
            return False, f"Expected '{expected['url_contains']}' in URL, got {url}"

        # Validate exact match
        if "expected" in expected:
            expected_val = expected["expected"]
            if isinstance(actual, dict):
                actual_val = actual.get("result")
            else:
                actual_val = actual

            if actual_val == expected_val:
                return True, None
            return False, f"Expected {expected_val}, got {actual_val}"

        # Validate title
        if "title" in expected:
            actual_title = actual.get("title", "") if isinstance(actual, dict) else ""
            if actual_title == expected["title"]:
                return True, None
            return False, f"Expected title '{expected['title']}', got '{actual_title}'"

        # Validate found
        if "found" in expected:
            actual_found = actual.get("found", False) if isinstance(actual, dict) else False
            if actual_found == expected["found"]:
                return True, None
            return False, f"Expected found={expected['found']}, got {actual_found}"

        # Validate min_count
        if "min_count" in expected:
            actual_count = actual.get("count", 0) if isinstance(actual, dict) else 0
            if actual_count >= expected["min_count"]:
                return True, None
            return False, f"Expected count >= {expected['min_count']}, got {actual_count}"

        # Validate element_role
        if "element_role" in expected:
            actual_role = actual.get("element_role", "") if isinstance(actual, dict) else ""
            if actual_role == expected["element_role"]:
                return True, None
            return False, f"Expected role '{expected['element_role']}', got '{actual_role}'"

        # Validate root_role
        if "root_role" in expected:
            actual_role = actual.get("root_role", "") if isinstance(actual, dict) else ""
            if actual_role == expected["root_role"]:
                return True, None
            return False, f"Expected root role '{expected['root_role']}', got '{actual_role}'"

        # Validate root_role_pattern (substring match)
        if "root_role_pattern" in expected:
            actual_role = actual.get("root_role", "") if isinstance(actual, dict) else ""
            pattern = expected["root_role_pattern"]
            if pattern.lower() in actual_role.lower():
                return True, None
            return False, f"Expected root role containing '{pattern}', got '{actual_role}'"

        # No specific validation rules matched
        return True, None


def run_evals(
    suites: list[str] | None = None,
    verbose: bool = True,
    report_path: str | Path | None = None,
) -> EvalReport:
    """
    Convenience function to run evals.

    Args:
        suites: Specific suites to run (None = all)
        verbose: Print progress
        report_path: Path to save JSON report (None = no save)

    Returns:
        EvalReport
    """
    runner = EvalRunner()
    report = runner.run(suites=suites, verbose=verbose)

    if report_path:
        report_path = Path(report_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w") as f:
            json.dump(report.to_json(), f, indent=2)

    return report
