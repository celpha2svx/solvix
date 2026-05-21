"""End-to-end regression tests for Solvix sample fixtures."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from core.doctor import build_doctor_report
from core.engine import _analyze_file, _analyze_project
from output.json_formatter import format_json_report

SAMPLES = Path(__file__).parent / "samples"
ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable


class SolvixTests(unittest.TestCase):
    def test_python_sample_labels(self) -> None:
        report = _analyze_file(SAMPLES / "sample.py", None, None)
        labels = {function.name: function.context.adjusted_label for function in report.functions}
        self.assertEqual(labels["nested_function"], "EXPENSIVE")
        self.assertEqual(labels["allocation_function"], "MODERATE")
        self.assertEqual(labels["clean_function"], "CHEAP")
        self.assertEqual(labels["recursive_function"], "MODERATE")
        self.assertEqual(labels["concat_function"], "MODERATE")

    def test_javascript_sample_detects_functions(self) -> None:
        report = _analyze_file(SAMPLES / "sample.js", None, None)
        self.assertEqual(report.summary.total_functions, 5)

    def test_rust_concat_detected(self) -> None:
        report = _analyze_file(SAMPLES / "sample.rs", None, None)
        targets = {function.name: function for function in report.functions}
        concat_function = targets["concat_function"]
        self.assertEqual(concat_function.context.adjusted_label, "MODERATE")
        self.assertIn(
            "string_concatenation_in_loop",
            [pattern.name for pattern in concat_function.patterns],
        )

    def test_single_function_mode(self) -> None:
        report = _analyze_file(SAMPLES / "sample.py", "nested_function", None)
        self.assertEqual(len(report.functions), 1)
        self.assertEqual(report.functions[0].name, "nested_function")

    def test_project_mode(self) -> None:
        report = _analyze_project(SAMPLES, None)
        self.assertGreaterEqual(report.summary.total_functions, 12)

    def test_json_output(self) -> None:
        report = _analyze_file(SAMPLES / "sample.py", None, None)
        payload = format_json_report(report)
        json.dumps(payload)
        self.assertEqual(payload["language"], "python")

    def test_doctor_report_shape(self) -> None:
        report = build_doctor_report()
        self.assertIn(report.overall_status, {"READY", "READY_WITH_AUTO_BOOTSTRAP", "DEGRADED"})
        self.assertIn(report.mode, {"native", "native-auto-bootstrap", "degraded"})
        self.assertIsInstance(report.providers, list)
        self.assertGreaterEqual(len(report.next_steps), 1)

    def test_output_json_file(self) -> None:
        output_path = ROOT / "tests" / "artifacts" / "report.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [
                str(PYTHON),
                "-m",
                "cli.main",
                "analyze",
                str(SAMPLES / "sample.py"),
                "--output",
                str(output_path),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn(f"Solvix: Report saved to {output_path}", result.stdout)
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["language"], "python")

    def test_output_text_file(self) -> None:
        output_path = ROOT / "tests" / "artifacts" / "report.txt"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [
                str(PYTHON),
                "-m",
                "cli.main",
                "analyze",
                str(SAMPLES / "sample.rs"),
                "--function",
                "concat_function",
                "--output",
                str(output_path),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn(f"Solvix: Report saved to {output_path}", result.stdout)
        text = output_path.read_text(encoding="utf-8")
        self.assertIn("Function : concat_function", text)
        self.assertIn("Cost     : MODERATE", text)
        self.assertIn("String Concatenation In Loop", text)


if __name__ == "__main__":
    unittest.main()
