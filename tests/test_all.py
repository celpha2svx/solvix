"""End-to-end regression tests for Solvix sample fixtures."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import unittest
import zipfile
from io import StringIO
from pathlib import Path

from click.testing import CliRunner

from cli.main import main as cli_main
from core.ai_overlay import AI_OVERLAY_DEFAULT_ASSIST_MODEL
from core.ai_overlay_payload import (
    AI_OVERLAY_MAX_EXAMPLES_PER_THEME,
    AI_OVERLAY_MAX_TOP_HOTSPOTS,
    AI_OVERLAY_MAX_TOP_LANES,
    AI_OVERLAY_MAX_TOP_THEMES,
    build_ai_overlay_payload,
)
from core.doctor import build_doctor_report
from core.engine import _analyze_file, _analyze_project
from core.report import (
    ActionLane,
    ConfidenceFactor,
    DependencyEvidenceItem,
    InsightTheme,
    LensLaneView,
    LensReport,
    LensThemeView,
    MultiLensSummary,
    NoiseDiagnostic,
    ProfileEvidence,
    ProjectProfile,
    ProjectSummary,
    SynthesisSummary,
)
from core.version import get_solvix_version
from output.json_formatter import format_json_report
from output import terminal_formatter
from output.text_formatter import format_text_report
from rich.console import Console
from scripts.generate_winget_assets import build_winget_portable_zips
from scripts.generate_winget_manifest import WINGET_PACKAGE_IDENTIFIER, build_winget_manifests

SAMPLES = Path(__file__).parent / "samples"
ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable


class StubAIOverlayProvider:
    provider_name = "stub_ai_overlay"

    def __init__(self, response=None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.calls: list[dict[str, object]] = []

    def generate(self, *, mode, model, payload, system_prompt, user_prompt):
        self.calls.append(
            {
                "mode": mode,
                "model": model,
                "payload": payload,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
            }
        )
        if self.error is not None:
            raise self.error
        return self.response


class GroundingDriftProvider:
    provider_name = "grounding_drift_stub"

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def generate(self, *, mode, model, payload, system_prompt, user_prompt):
        self.calls.append({"mode": mode, "model": model, "payload": payload})
        valid_theme_key = payload.top_themes[0]["key"] if payload.top_themes else "missing-theme"
        valid_lane_key = payload.top_lanes[0]["key"] if payload.top_lanes else "missing-lane"
        valid_hotspot = payload.top_hotspots[0] if payload.top_hotspots else {"file": "missing.py", "function": "missing"}
        return {
            "executive_summary": "The bounded deterministic payload points to a small number of priority themes.",
            "maintainer_plan": [
                "Start with the top deterministic lane first.",
                "Confirm the highest-priority hotspots are production-facing.",
                "Use the deterministic lens ordering to sequence the next fixes.",
            ],
            "lens_explanation": "The AI overlay is following the deterministic default lens rather than inventing a new ordering.",
            "grounded_theme_keys": ["invented-theme", valid_theme_key],
            "grounded_lane_keys": ["invented-lane", valid_lane_key],
            "grounded_hotspots": [
                {"file": "invented.py", "function": "invented"},
                {"file": valid_hotspot["file"], "function": valid_hotspot["function"]},
            ],
            "caveats": ["Ground this in deterministic data."],
        }


class SolvixTests(unittest.TestCase):
    def _scratch_dir(self, name: str) -> Path:
        path = ROOT / "tests" / "artifacts" / name
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def _write_file(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def _top_hotspot(self, report):
        hotspots = report.summary.prioritized_hotspots or report.summary.top_functions
        self.assertTrue(hotspots)
        return hotspots[0]

    def _synthesis(self, report):
        self.assertIsNotNone(report.synthesis)
        return report.synthesis

    def _lane_keys(self, report) -> list[str]:
        return [lane.key for lane in self._synthesis(report).action_lanes]

    def _theme_keys(self, report) -> list[str]:
        return [theme.key for theme in self._synthesis(report).dominant_themes]

    def _theme_keys_for_file(self, report, file_suffix: str) -> list[str]:
        keys: list[str] = []
        for theme in self._synthesis(report).dominant_themes:
            if any(example["file"].endswith(file_suffix) for example in theme.representative_examples):
                keys.append(theme.key)
        return keys

    def _multi_lens(self, report):
        self.assertIsNotNone(report.multi_lens)
        return report.multi_lens

    def _lens_report(self, report, lens: str | None = None):
        multi_lens = self._multi_lens(report)
        target = lens or multi_lens.default_lens
        for item in multi_lens.reports:
            if item.lens == target:
                return item
        self.fail(f"Lens report not found: {target}")

    def _stage5_contract_fixture(self):
        hotspots = [
            {
                "label": "EXPENSIVE" if index % 2 == 0 else "MODERATE",
                "file": f"services/api_{index}.py",
                "function": f"hotspot_{index}",
                "relevance_score": 90 - index,
                "relevance_level": "urgent" if index < 3 else "high",
                "project_priority_label": "fix_first" if index < 3 else "high_priority",
                "relevance_reason": f"Hotspot {index} is on a critical request path.",
                "zone": "critical",
            }
            for index in range(10)
        ]
        themes = [
            InsightTheme(
                key=f"request_path_hotspots:theme_{index}",
                title=f"Theme {index}",
                summary=f"Theme {index} summarizes repeated request-path pressure.",
                relevance_score=100 - index,
                priority_label="fix_first" if index < 2 else "high_priority",
                pattern_families=["loop_amplification", "allocation_churn"],
                representative_examples=[
                    {
                        "file": f"services/api_{index}.py",
                        "function": f"handler_{index}_a",
                        "label": "EXPENSIVE",
                        "zone": "critical",
                    },
                    {
                        "file": f"services/api_{index}.py",
                        "function": f"handler_{index}_b",
                        "label": "MODERATE",
                        "zone": "critical",
                    },
                    {
                        "file": f"services/api_{index}.py",
                        "function": f"handler_{index}_c",
                        "label": "MODERATE",
                        "zone": "supporting",
                    },
                ],
                affected_files=2,
                affected_functions=3,
                critical_zone_hits=2,
                noise_zone_hits=0,
                dominant_zone="critical",
                repetition_score=20 - index,
            )
            for index in range(7)
        ]
        lanes = [
            ActionLane(
                key=f"lane_{index}",
                title=f"Lane {index}",
                why_now=f"Lane {index} collects the strongest deterministic follow-up work.",
                recommended_order=index + 1,
                related_theme_keys=[themes[index % len(themes)].key],
                representative_targets=[{"file": f"services/api_{index}.py", "function": f"target_{index}"}],
            )
            for index in range(5)
        ]
        default_report = LensReport(
            lens="performance",
            title="Performance Lens",
            summary="The deterministic default lens emphasizes request-path throughput.",
            top_themes=[
                LensThemeView(
                    theme_key=theme.key,
                    title=theme.title,
                    base_theme_score=theme.relevance_score,
                    score=theme.relevance_score + 5,
                    priority_label=theme.priority_label,
                    reason="Performance lens boosts request-path themes.",
                )
                for theme in themes[:4]
            ],
            top_lanes=[
                LensLaneView(
                    lane_key=lane.key,
                    title=lane.title,
                    score=90 - index,
                    reason="Performance lens keeps this lane near the top.",
                    related_theme_keys=list(lane.related_theme_keys),
                )
                for index, lane in enumerate(lanes)
            ],
            recommended_first_action="Start with the request-path lane first.",
        )
        multi_lens = MultiLensSummary(
            default_lens="performance",
            default_lens_reason="The repository shape and objectives are request-path heavy.",
            available_lenses=["performance", "cloud_cost", "maintainability"],
            reports=[
                default_report,
                LensReport(
                    lens="cloud_cost",
                    title="Cloud Cost Lens",
                    summary="Cloud cost would reorder the same deterministic evidence differently.",
                    top_lanes=default_report.top_lanes[:2],
                    recommended_first_action="Compare repeated request-path work with cloud-sensitive fan-out.",
                ),
            ],
        )
        profile = ProjectProfile(
            primary_profile="web_backend",
            secondary_profiles=["cli_tool"],
            execution_models=["request_response", "distributed_services"],
            surfaces=["http", "cli"],
            confidence="high",
            confidence_score=11,
            project_type="web_backend",
            primary_objectives=["request_overhead", "latency", "maintainability"],
            secondary_objectives=["startup_time"],
            primary_languages=["Python"],
            critical_zones=["services", "api"],
            noise_zones=["tests", "docs"],
            zone_classification=[],
            detected_markers=["fastapi", "click"],
            evidence=ProfileEvidence(
                dependency_markers=["fastapi", "click"],
                dependency_details=[
                    DependencyEvidenceItem(marker="fastapi", manifest="pyproject.toml", source="project.dependencies")
                ],
                directory_markers=["services", "api"],
                entrypoint_markers=["main.py"],
                language_markers=["python"],
                confidence_factors=[
                    ConfidenceFactor(
                        name="dependency_signal",
                        weight=4,
                        matched=True,
                        evidence="FastAPI dependency marker was found.",
                    )
                ],
            ),
            explanation="Stage 1 classified the repository as a request-path-heavy web backend.",
            web_shape="api_service",
            service_topology="distributed_monolith",
            hybrid_shape=None,
        )
        summary = ProjectSummary(
            files_analyzed=6,
            languages_found=["Python"],
            total_functions=24,
            clean_functions=8,
            flagged_functions=16,
            top_functions=list(hotspots),
            risk_level="HIGH",
            why_it_matters="Most flagged work sits on deterministic request paths.",
            recommended_next_step="Start with the top deterministic request-path lane.",
            prioritized_hotspots=list(hotspots),
            discounted_functions=4,
        )
        synthesis = SynthesisSummary(
            dominant_themes=themes,
            action_lanes=lanes,
            noise_diagnostic=NoiseDiagnostic(
                discounted_functions=4,
                dominant_noise_zones=["tests", "docs"],
                noise_ratio=0.2,
                summary="Noise stays present but does not dominate the deterministic ranking.",
            ),
            repository_story="Request-path pressure dominates the deterministic repository story.",
            maintainer_brief="Start with the request path, then clean up repeated supporting churn.",
        )
        return profile, summary, synthesis, multi_lens

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
        self.assertIn(report.summary.risk_level, {"LOW", "MODERATE", "HIGH"})
        self.assertTrue(report.summary.why_it_matters)
        self.assertTrue(report.summary.recommended_next_step)
        self.assertTrue(report.profile.project_type)
        self.assertTrue(report.profile.primary_profile)
        self.assertIn(report.profile.confidence, {"low", "moderate", "high"})
        self.assertIsInstance(report.profile.confidence_score, int)
        self.assertIsInstance(report.profile.secondary_profiles, list)
        self.assertIsInstance(report.profile.execution_models, list)
        self.assertIsInstance(report.profile.surfaces, list)
        self.assertTrue(report.profile.primary_objectives)
        self.assertIsInstance(report.profile.noise_zones, list)
        self.assertIsInstance(report.profile.zone_classification, list)
        self.assertIsInstance(report.profile.evidence.confidence_factors, list)
        self.assertIsInstance(report.summary.prioritized_hotspots, list)
        if report.summary.prioritized_hotspots:
            self.assertIn("relevance_score", report.summary.prioritized_hotspots[0])

    def test_project_mode_skips_files_without_functions(self) -> None:
        temp_dir = self._scratch_dir("project_skip_case")
        no_functions = temp_dir / "contracts.py"
        has_functions = temp_dir / "worker.py"
        empty_module = temp_dir / "__init__.py"
        no_functions.write_text("NAME = 'solvix'\nVERSION = '1.0'\n", encoding="utf-8")
        has_functions.write_text(
            "def run_task(items):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        total += item\n"
            "    return total\n",
            encoding="utf-8",
        )
        empty_module.write_text("", encoding="utf-8")

        report = _analyze_project(temp_dir, None)
        self.assertEqual(report.summary.files_analyzed, 1)
        self.assertEqual(report.summary.total_functions, 1)

    def test_json_output(self) -> None:
        report = _analyze_file(SAMPLES / "sample.py", None, None)
        payload = format_json_report(report)
        json.dumps(payload)
        self.assertEqual(payload["language"], "python")
        self.assertIn("relevance", payload)

    def test_json_output_preserves_raw_cost_label(self) -> None:
        temp_dir = self._scratch_dir("json_raw_cost_label")
        sample_file = temp_dir / "service.py"
        self._write_file(
            sample_file,
            "def setup_cache(items):\n"
            "    values = []\n"
            "    for item in items:\n"
            "        values.append(item)\n"
            "    return values\n",
        )
        report = _analyze_file(sample_file, None, None)
        payload = format_json_report(report)
        function = payload["functions"][0]
        self.assertEqual(function["cost"]["label"], report.functions[0].cost.label)
        self.assertEqual(function["context"]["urgency_modifier"], report.functions[0].context.urgency_modifier)
        self.assertNotEqual(function["cost"]["label"], report.functions[0].context.adjusted_label)

    def test_json_output_uses_shared_version_source(self) -> None:
        report = _analyze_file(SAMPLES / "sample.py", None, None)
        payload = format_json_report(report)
        self.assertEqual(payload["solvix_version"], get_solvix_version())

    def test_json_output_saved_project_prints_summary_not_full_payload(self) -> None:
        output_path = self._scratch_dir("project_json_output") / "report.json"
        result = subprocess.run(
            [
                str(PYTHON),
                "-m",
                "cli.main",
                "analyze",
                str(SAMPLES),
                "--project",
                "--json",
                "--output",
                str(output_path),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("Solvix: Full JSON project report saved.", result.stdout)
        self.assertIn("Risk level", result.stdout)
        self.assertNotIn('"files":', result.stdout)
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["solvix_version"], get_solvix_version())

    def test_cli_help_is_example_driven(self) -> None:
        runner = CliRunner()

        root = runner.invoke(cli_main, ["--help"])
        self.assertEqual(root.exit_code, 0, root.output)
        self.assertIn("Solvix analyzes source code cost", root.output)
        self.assertIn("Common examples:", root.output)
        self.assertIn("solvix analyze src --project --json --output report.json", root.output)
        self.assertIn("solvix bootstrap-parsers --all", root.output)
        self.assertIn("AI is optional", root.output)

        analyze = runner.invoke(cli_main, ["analyze", "--help"])
        self.assertEqual(analyze.exit_code, 0, analyze.output)
        self.assertIn("File mode", analyze.output)
        self.assertIn("Project mode", analyze.output)
        self.assertIn("solvix analyze app.py --function parse_invoice", analyze.output)
        self.assertIn("solvix analyze src --project --ai-mode assist", analyze.output)

        doctor = runner.invoke(cli_main, ["doctor", "--help"])
        self.assertEqual(doctor.exit_code, 0, doctor.output)
        self.assertIn("parser health, cache state", doctor.output)
        self.assertIn("solvix doctor --json", doctor.output)

        bootstrap = runner.invoke(cli_main, ["bootstrap-parsers", "--help"])
        self.assertEqual(bootstrap.exit_code, 0, bootstrap.output)
        self.assertIn("offline or restricted machines", bootstrap.output)
        self.assertIn("solvix bootstrap-parsers javascript typescript rust", bootstrap.output)

    def test_project_analysis_emits_operational_status_phases(self) -> None:
        temp_dir = self._scratch_dir("project_status_phases")
        self._write_file(
            temp_dir / "app.py",
            "def handle(items):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        total += item\n"
            "    return total\n",
        )
        statuses: list[str] = []

        report = _analyze_project(temp_dir, None, status_callback=statuses.append)

        self.assertEqual(report.summary.files_analyzed, 1)
        for status in [
            "Discovering source files",
            "Profiling repository",
            "Scoring functions",
            "Synthesizing project themes",
            "Preparing multi-lens views",
        ]:
            self.assertIn(status, statuses)
        self.assertNotIn("Generating AI overlay", statuses)

    def test_ai_overlay_emits_optional_progress_statuses(self) -> None:
        temp_dir = self._scratch_dir("ai_overlay_status_phases")
        self._write_file(
            temp_dir / "api" / "handlers.py",
            "def handle_request(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "pyproject.toml",
            "[project]\nname='ai-status'\ndependencies=['fastapi>=1.0']\n",
        )
        provider = StubAIOverlayProvider(
            response={
                "executive_summary": "The bounded deterministic payload points to request-path pressure first.",
                "maintainer_plan": [
                    "Start with the top deterministic lane.",
                    "Validate the highest-priority hotspot.",
                    "Keep the deterministic report as source of truth.",
                ],
                "lens_explanation": "The default deterministic lens shaped the overlay.",
                "grounded_theme_keys": [],
                "grounded_lane_keys": [],
                "grounded_hotspots": [],
                "caveats": [],
            }
        )
        statuses: list[str] = []

        report = _analyze_project(
            temp_dir,
            None,
            ai_mode="assist",
            ai_provider=provider,
            status_callback=statuses.append,
        )

        self.assertEqual(report.ai_overlay.status, "completed")
        for status in [
            "Generating AI overlay",
            "Compressing deterministic report",
            "Contacting AI provider",
            "Grounding overlay output",
            "AI overlay complete",
        ]:
            self.assertIn(status, statuses)

    def test_winget_generators_create_portable_zip_and_manifests(self) -> None:
        temp_dir = self._scratch_dir("winget_generation")
        asset_dir = temp_dir / "assets"
        output_dir = temp_dir / "release-metadata"
        asset_dir.mkdir()
        windows_binary = asset_dir / "solvix-windows-x64.exe"
        windows_binary.write_bytes(b"fake solvix binary")

        created = build_winget_portable_zips(asset_dir, output_dir)

        zip_path = output_dir / "solvix-windows-x64-portable.zip"
        checksum_path = output_dir / "solvix-windows-x64-portable.zip.sha256"
        self.assertIn(zip_path, created)
        self.assertIn(checksum_path, created)
        with zipfile.ZipFile(zip_path) as archive:
            self.assertEqual(archive.namelist(), ["solvix.exe"])
            self.assertEqual(archive.read("solvix.exe"), b"fake solvix binary")

        manifest_paths = build_winget_manifests(
            version="v0.3.0",
            repo="celpha2svx/solvix",
            asset_dir=output_dir,
            output_dir=temp_dir / "winget",
        )

        installer_manifest = next(path for path in manifest_paths if path.name.endswith(".installer.yaml"))
        locale_manifest = next(path for path in manifest_paths if path.name.endswith(".locale.en-US.yaml"))
        installer_text = installer_manifest.read_text(encoding="utf-8")
        locale_text = locale_manifest.read_text(encoding="utf-8")
        self.assertIn(f'PackageIdentifier: "{WINGET_PACKAGE_IDENTIFIER}"', installer_text)
        self.assertIn('InstallerType: "zip"', installer_text)
        self.assertIn('NestedInstallerType: "portable"', installer_text)
        self.assertIn('PortableCommandAlias: "solvix"', installer_text)
        self.assertIn("solvix-windows-x64-portable.zip", installer_text)
        self.assertIn('PackageName: "Solvix"', locale_text)

    def test_project_profile_infers_framework_shape(self) -> None:
        temp_dir = self._scratch_dir("project_profile_framework")
        (temp_dir / "src").mkdir()
        (temp_dir / "tests").mkdir()
        (temp_dir / "docs").mkdir()
        (temp_dir / "src" / "app.py").write_text(
            "def dispatch_request():\n    return 'ok'\n",
            encoding="utf-8",
        )
        (temp_dir / "tests" / "test_app.py").write_text(
            "def test_dispatch():\n    assert True\n",
            encoding="utf-8",
        )
        (temp_dir / "pyproject.toml").write_text(
            "[project]\nname='demo'\ndependencies=['flask>=3.0']\n",
            encoding="utf-8",
        )

        report = _analyze_project(temp_dir, None)
        self.assertEqual(report.profile.project_type, "framework_library")
        self.assertEqual(report.profile.primary_profile, "framework_library")
        self.assertIn("request_response", report.profile.execution_models)
        self.assertIn("http", report.profile.surfaces)
        self.assertIn("tests", report.profile.noise_zones)
        self.assertIn("api_stability", report.profile.primary_objectives)
        self.assertIn("src", report.profile.critical_zones)
        self.assertGreaterEqual(report.profile.confidence_score, 5)
        self.assertTrue(
            any(item.manifest == "pyproject.toml" and item.marker == "flask" for item in report.profile.evidence.dependency_details)
        )
        src_report = next(item for item in report.files if item.file.endswith("src\\app.py"))
        test_report = next(item for item in report.files if item.file.endswith("tests\\test_app.py"))
        self.assertEqual(src_report.summary.zone, "critical")
        self.assertEqual(test_report.summary.zone, "noise")
        self.assertIn("critical_directory", src_report.zone_reasons)
        self.assertIn("noise_directory", test_report.zone_reasons)

    def test_project_profile_infers_mixed_surfaces(self) -> None:
        temp_dir = self._scratch_dir("project_profile_mixed")
        (temp_dir / "services").mkdir()
        (temp_dir / "workers").mkdir()
        (temp_dir / "cli").mkdir()
        (temp_dir / "services" / "api.py").write_text(
            "def route_request():\n    return 1\n",
            encoding="utf-8",
        )
        (temp_dir / "workers" / "jobs.py").write_text(
            "def run_job(items):\n    return sum(items)\n",
            encoding="utf-8",
        )
        (temp_dir / "cli" / "main.py").write_text(
            "def main():\n    return 0\n",
            encoding="utf-8",
        )
        (temp_dir / "pyproject.toml").write_text(
            "[project]\nname='demo'\ndependencies=['fastapi>=1.0','click>=8.0']\n",
            encoding="utf-8",
        )

        report = _analyze_project(temp_dir, None)
        self.assertEqual(report.profile.primary_profile, "web_backend")
        self.assertIn("cli_tool", report.profile.secondary_profiles)
        self.assertIn("distributed_services", report.profile.execution_models)
        self.assertIn("background_jobs", report.profile.execution_models)
        self.assertIn("http", report.profile.surfaces)
        self.assertIn("cli", report.profile.surfaces)
        self.assertIn(report.profile.confidence, {"moderate", "high"})
        self.assertTrue(
            any(item.manifest == "pyproject.toml" and item.marker == "fastapi" for item in report.profile.evidence.dependency_details)
        )
        cli_report = next(item for item in report.files if item.file.endswith("cli\\main.py"))
        self.assertEqual(cli_report.summary.zone, "critical")

    def test_project_profile_parses_package_json_structurally(self) -> None:
        temp_dir = self._scratch_dir("project_profile_package_json")
        (temp_dir / "src").mkdir()
        (temp_dir / "src" / "server.js").write_text(
            "function handleRequest() { return 1; }\n",
            encoding="utf-8",
        )
        (temp_dir / "package.json").write_text(
            json.dumps(
                {
                    "name": "demo",
                    "dependencies": {"express": "^4.0.0"},
                    "devDependencies": {"jest": "^29.0.0"},
                }
            ),
            encoding="utf-8",
        )

        report = _analyze_project(temp_dir, None)
        self.assertEqual(report.profile.primary_profile, "web_backend")
        self.assertTrue(
            any(item.manifest == "package.json" and item.source == "dependencies" and item.marker == "express"
                for item in report.profile.evidence.dependency_details)
        )
        self.assertGreaterEqual(report.profile.confidence_score, 5)

    def test_project_profile_distinguishes_api_service(self) -> None:
        temp_dir = self._scratch_dir("project_profile_api_service")
        (temp_dir / "api").mkdir()
        (temp_dir / "routes").mkdir()
        (temp_dir / "api" / "handlers.py").write_text(
            "def get_status():\n    return {'ok': True}\n",
            encoding="utf-8",
        )
        (temp_dir / "routes" / "health.py").write_text(
            "def register_routes():\n    return ['health']\n",
            encoding="utf-8",
        )
        (temp_dir / "pyproject.toml").write_text(
            "[project]\nname='api-demo'\ndependencies=['fastapi>=1.0','uvicorn>=0.1']\n",
            encoding="utf-8",
        )

        report = _analyze_project(temp_dir, None)
        self.assertEqual(report.profile.primary_profile, "web_backend")
        self.assertEqual(report.profile.web_shape, "api_service")
        self.assertIsNone(report.profile.hybrid_shape)
        self.assertGreaterEqual(report.profile.confidence_score, 8)
        api_report = next(item for item in report.files if item.file.endswith("api\\handlers.py"))
        self.assertIn("web_route_path", api_report.zone_reasons)

    def test_project_profile_distinguishes_website_web_app(self) -> None:
        temp_dir = self._scratch_dir("project_profile_website_web_app")
        (temp_dir / "frontend").mkdir()
        (temp_dir / "pages").mkdir()
        (temp_dir / "components").mkdir()
        (temp_dir / "frontend" / "app.ts").write_text(
            "export function bootApp() { return 'ok'; }\n",
            encoding="utf-8",
        )
        (temp_dir / "pages" / "home.ts").write_text(
            "export function homePage() { return 'home'; }\n",
            encoding="utf-8",
        )
        (temp_dir / "components" / "nav.ts").write_text(
            "export function renderNav() { return 'nav'; }\n",
            encoding="utf-8",
        )
        (temp_dir / "package.json").write_text(
            json.dumps(
                {
                    "name": "webapp-demo",
                    "dependencies": {"react": "^18.0.0", "next": "^14.0.0"},
                }
            ),
            encoding="utf-8",
        )

        report = _analyze_project(temp_dir, None)
        self.assertEqual(report.profile.primary_profile, "web_backend")
        self.assertEqual(report.profile.web_shape, "website_web_app")
        self.assertIn("web_ui", report.profile.surfaces)
        self.assertGreaterEqual(report.profile.confidence_score, 8)
        page_report = next(item for item in report.files if item.file.endswith("pages\\home.ts"))
        self.assertIn("website_ui_path", page_report.zone_reasons)

    def test_project_profile_distinguishes_distributed_monolith(self) -> None:
        temp_dir = self._scratch_dir("project_profile_distributed_monolith")
        (temp_dir / "services").mkdir()
        (temp_dir / "gateway").mkdir()
        (temp_dir / "workers").mkdir()
        (temp_dir / "services" / "billing.py").write_text(
            "def charge_user():\n    return True\n",
            encoding="utf-8",
        )
        (temp_dir / "gateway" / "main.py").write_text(
            "def main():\n    return 0\n",
            encoding="utf-8",
        )
        (temp_dir / "workers" / "jobs.py").write_text(
            "def drain_queue():\n    return 1\n",
            encoding="utf-8",
        )
        (temp_dir / "pyproject.toml").write_text(
            "[project]\nname='mono-demo'\ndependencies=['fastapi>=1.0']\n",
            encoding="utf-8",
        )

        report = _analyze_project(temp_dir, None)
        self.assertIn("distributed_services", report.profile.execution_models)
        self.assertEqual(report.profile.service_topology, "distributed_monolith")

    def test_project_profile_distinguishes_microservices(self) -> None:
        temp_dir = self._scratch_dir("project_profile_microservices")
        (temp_dir / "services" / "auth").mkdir(parents=True)
        (temp_dir / "services" / "billing").mkdir(parents=True)
        (temp_dir / "gateway").mkdir()
        (temp_dir / "services" / "auth" / "main.py").write_text(
            "def main():\n    return 'auth'\n",
            encoding="utf-8",
        )
        (temp_dir / "services" / "billing" / "server.py").write_text(
            "def main():\n    return 'billing'\n",
            encoding="utf-8",
        )
        (temp_dir / "gateway" / "router.py").write_text(
            "def route_request():\n    return 'gateway'\n",
            encoding="utf-8",
        )
        (temp_dir / "pyproject.toml").write_text(
            "[project]\nname='micro-demo'\ndependencies=['fastapi>=1.0']\n",
            encoding="utf-8",
        )

        report = _analyze_project(temp_dir, None)
        self.assertIn("distributed_services", report.profile.execution_models)
        self.assertEqual(report.profile.service_topology, "microservices")
        self.assertGreaterEqual(report.profile.confidence_score, 8)

    def test_project_profile_detects_device_firmware_cloud(self) -> None:
        temp_dir = self._scratch_dir("project_profile_device_firmware_cloud")
        self._write_file(temp_dir / "firmware" / "drivers" / "sensor.c", "int read_sensor(void) {\n    return 1;\n}\n")
        self._write_file(temp_dir / "cloud" / "api" / "app.py", "def route_request():\n    return 'ok'\n")
        self._write_file(
            temp_dir / "pyproject.toml",
            "[project]\nname='hybrid-demo'\ndependencies=['fastapi>=1.0']\n",
        )
        self._write_file(
            temp_dir / "platformio.ini",
            "[env:demo]\nplatform = espressif32\nframework = arduino\n",
        )

        report = _analyze_project(temp_dir, None)
        self.assertEqual(report.profile.primary_profile, "device_firmware")
        self.assertIn("web_backend", report.profile.secondary_profiles)
        self.assertEqual(report.profile.hybrid_shape, "device_firmware_cloud")
        firmware_report = next(item for item in report.files if item.file.endswith("firmware\\drivers\\sensor.c"))
        cloud_report = next(item for item in report.files if item.file.endswith("cloud\\api\\app.py"))
        self.assertEqual(firmware_report.summary.zone, "critical")
        self.assertEqual(cloud_report.summary.zone, "critical")
        self.assertIn("firmware_path", firmware_report.zone_reasons)
        self.assertIn("hybrid_cloud_control_path", cloud_report.zone_reasons)

    def test_project_profile_detects_device_firmware_serverless(self) -> None:
        temp_dir = self._scratch_dir("project_profile_device_firmware_serverless")
        self._write_file(temp_dir / "firmware" / "drivers" / "sensor.c", "int read_sensor(void) {\n    return 1;\n}\n")
        self._write_file(temp_dir / "functions" / "main.py", "def main():\n    return 'worker'\n")
        self._write_file(
            temp_dir / "pyproject.toml",
            "[project]\nname='hybrid-demo'\ndependencies=['functions-framework>=3.0']\n",
        )
        self._write_file(
            temp_dir / "platformio.ini",
            "[env:demo]\nplatform = espressif32\nframework = arduino\n",
        )

        report = _analyze_project(temp_dir, None)
        self.assertEqual(report.profile.primary_profile, "device_firmware")
        self.assertIn("serverless_application", report.profile.secondary_profiles)
        self.assertEqual(report.profile.hybrid_shape, "device_firmware_serverless")
        function_report = next(item for item in report.files if item.file.endswith("functions\\main.py"))
        self.assertIn("serverless_function_path", function_report.zone_reasons)

    def test_project_profile_infers_serverless_application(self) -> None:
        temp_dir = self._scratch_dir("project_profile_serverless")
        self._write_file(temp_dir / "functions" / "handler.py", "def run_handler():\n    return 1\n")
        self._write_file(
            temp_dir / "pyproject.toml",
            "[project]\nname='serverless-demo'\ndependencies=['functions-framework>=3.0']\n",
        )

        report = _analyze_project(temp_dir, None)
        self.assertEqual(report.profile.primary_profile, "serverless_application")
        self.assertIn("serverless", report.profile.execution_models)

    def test_project_profile_infers_mobile_application(self) -> None:
        temp_dir = self._scratch_dir("project_profile_mobile")
        self._write_file(temp_dir / "android" / "app.kt", "fun launchApp(): Int {\n    return 1\n}\n")
        self._write_file(
            temp_dir / "package.json",
            json.dumps({"name": "mobile-demo", "dependencies": {"react-native": "^0.76.0"}}),
        )

        report = _analyze_project(temp_dir, None)
        self.assertEqual(report.profile.primary_profile, "mobile_application")
        self.assertIn("mobile", report.profile.surfaces)

    def test_project_profile_infers_desktop_application(self) -> None:
        temp_dir = self._scratch_dir("project_profile_desktop")
        self._write_file(temp_dir / "desktop" / "main.js", "function bootDesktop() { return 1; }\n")
        self._write_file(
            temp_dir / "package.json",
            json.dumps({"name": "desktop-demo", "dependencies": {"electron": "^31.0.0"}}),
        )

        report = _analyze_project(temp_dir, None)
        self.assertEqual(report.profile.primary_profile, "desktop_application")
        self.assertIn("desktop", report.profile.surfaces)

    def test_project_profile_infers_cli_tool(self) -> None:
        temp_dir = self._scratch_dir("project_profile_cli")
        self._write_file(temp_dir / "cli" / "main.py", "def main():\n    return 0\n")
        self._write_file(
            temp_dir / "pyproject.toml",
            "[project]\nname='cli-demo'\ndependencies=['click>=8.0']\n",
        )

        report = _analyze_project(temp_dir, None)
        self.assertEqual(report.profile.primary_profile, "cli_tool")
        self.assertIn("cli", report.profile.surfaces)

    def test_project_profile_infers_data_pipeline(self) -> None:
        temp_dir = self._scratch_dir("project_profile_data_pipeline")
        self._write_file(temp_dir / "pipelines" / "daily.py", "def run_pipeline():\n    return 1\n")
        self._write_file(temp_dir / "jobs" / "worker.py", "def queue_job():\n    return 1\n")
        self._write_file(
            temp_dir / "pyproject.toml",
            "[project]\nname='pipeline-demo'\ndependencies=['airflow>=2.0','pandas>=2.0']\n",
        )

        report = _analyze_project(temp_dir, None)
        self.assertEqual(report.profile.primary_profile, "data_pipeline")
        self.assertIn("background_jobs", report.profile.execution_models)

    def test_project_profile_infers_sdk_library(self) -> None:
        temp_dir = self._scratch_dir("project_profile_sdk")
        self._write_file(temp_dir / "src" / "client.py", "def fetch_client():\n    return 1\n")
        self._write_file(
            temp_dir / "pyproject.toml",
            "[project]\nname='sdk-demo'\ndependencies=['acme-sdk>=1.0']\n",
        )

        report = _analyze_project(temp_dir, None)
        self.assertEqual(report.profile.primary_profile, "sdk_library")
        self.assertIn("sdk", report.profile.surfaces)

    def test_project_profile_infers_test_heavy_repository(self) -> None:
        temp_dir = self._scratch_dir("project_profile_test_heavy")
        self._write_file(temp_dir / "tests" / "test_worker.py", "def test_worker():\n    return True\n")
        self._write_file(temp_dir / "specs" / "worker_spec.py", "def spec_worker():\n    return True\n")
        self._write_file(temp_dir / "docs" / "examples.py", "def docs_example():\n    return True\n")

        report = _analyze_project(temp_dir, None)
        self.assertEqual(report.profile.primary_profile, "test_heavy_repository")
        self.assertIn("tests", report.profile.noise_zones)

    def test_stage2_relevance_framework_library_discounts_tests(self) -> None:
        temp_dir = self._scratch_dir("stage2_framework_library")
        self._write_file(
            temp_dir / "src" / "dispatch.py",
            "def dispatch_request(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "tests" / "test_dispatch.py",
            "def test_dispatch(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "docs" / "example.py",
            "def docs_example(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "pyproject.toml",
            "[project]\nname='framework-demo'\ndependencies=['flask>=3.0']\n",
        )

        report = _analyze_project(temp_dir, None)
        hotspot = self._top_hotspot(report)
        self.assertEqual(report.profile.primary_profile, "framework_library")
        self.assertIn("src\\dispatch.py", hotspot["file"])
        self.assertEqual(hotspot["function"], "dispatch_request")
        src_report = next(item for item in report.files if item.file.endswith("src\\dispatch.py"))
        test_report = next(item for item in report.files if item.file.endswith("tests\\test_dispatch.py"))
        self.assertGreater(src_report.functions[0].relevance.score, test_report.functions[0].relevance.score)

    def test_stage2_relevance_api_service_prefers_request_path(self) -> None:
        temp_dir = self._scratch_dir("stage2_api_service")
        self._write_file(
            temp_dir / "api" / "handlers.py",
            "def handle_request(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "app.py",
            "def boot_service(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "pyproject.toml",
            "[project]\nname='api-demo'\ndependencies=['fastapi>=1.0','uvicorn>=0.1']\n",
        )

        report = _analyze_project(temp_dir, None)
        hotspot = self._top_hotspot(report)
        self.assertEqual(report.profile.web_shape, "api_service")
        self.assertIn("api\\handlers.py", hotspot["file"])
        self.assertEqual(hotspot["function"], "handle_request")

    def test_stage2_relevance_website_prefers_ui_surface(self) -> None:
        temp_dir = self._scratch_dir("stage2_website")
        self._write_file(
            temp_dir / "pages" / "home.ts",
            "export function render_page(items: number[], lookup: number[]) {\n"
            "  let total = 0;\n"
            "  for (const item of items) {\n"
            "    for (const other of lookup) {\n"
            "      if (item === other) {\n"
            "        total += 1;\n"
            "      }\n"
            "    }\n"
            "  }\n"
            "  return total;\n"
            "}\n",
        )
        self._write_file(
            temp_dir / "docs" / "example.ts",
            "export function docs_example(items: number[], lookup: number[]) {\n"
            "  let total = 0;\n"
            "  for (const item of items) {\n"
            "    for (const other of lookup) {\n"
            "      if (item === other) {\n"
            "        total += 1;\n"
            "      }\n"
            "    }\n"
            "  }\n"
            "  return total;\n"
            "}\n",
        )
        self._write_file(
            temp_dir / "package.json",
            json.dumps({"name": "webapp-demo", "dependencies": {"react": "^18.0.0", "next": "^14.0.0"}}),
        )

        report = _analyze_project(temp_dir, None)
        hotspot = self._top_hotspot(report)
        self.assertEqual(report.profile.web_shape, "website_web_app")
        self.assertIn("pages\\home.ts", hotspot["file"])
        self.assertEqual(hotspot["function"], "render_page")

    def test_stage2_relevance_cli_prefers_command_startup(self) -> None:
        temp_dir = self._scratch_dir("stage2_cli")
        self._write_file(
            temp_dir / "cli" / "main.py",
            "def main(items):\n"
            "    values = []\n"
            "    for item in items:\n"
            "        values.append(str(item))\n"
            "    return ''.join(values)\n",
        )
        self._write_file(
            temp_dir / "src" / "helpers.py",
            "def helper_logic(items):\n"
            "    values = []\n"
            "    for item in items:\n"
            "        values.append(str(item))\n"
            "    return ''.join(values)\n",
        )
        self._write_file(
            temp_dir / "pyproject.toml",
            "[project]\nname='cli-demo'\ndependencies=['click>=8.0']\n",
        )

        report = _analyze_project(temp_dir, None)
        hotspot = self._top_hotspot(report)
        self.assertEqual(report.profile.primary_profile, "cli_tool")
        self.assertIn("cli\\main.py", hotspot["file"])
        self.assertEqual(hotspot["function"], "main")

    def test_stage2_relevance_data_pipeline_prefers_throughput_path(self) -> None:
        temp_dir = self._scratch_dir("stage2_data_pipeline")
        self._write_file(
            temp_dir / "pipelines" / "daily.py",
            "def run_pipeline(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "docs" / "example.py",
            "def docs_example(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "pyproject.toml",
            "[project]\nname='pipeline-demo'\ndependencies=['airflow>=2.0','pandas>=2.0']\n",
        )

        report = _analyze_project(temp_dir, None)
        hotspot = self._top_hotspot(report)
        self.assertEqual(report.profile.primary_profile, "data_pipeline")
        self.assertIn("pipelines\\daily.py", hotspot["file"])
        self.assertEqual(hotspot["function"], "run_pipeline")

    def test_stage2_relevance_serverless_boosts_startup_handler(self) -> None:
        temp_dir = self._scratch_dir("stage2_serverless")
        self._write_file(
            temp_dir / "functions" / "main.py",
            "def boot_handler(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "src" / "worker.py",
            "def process_records(items):\n"
            "    values = []\n"
            "    for item in items:\n"
            "        values.append(item)\n"
            "    return values\n",
        )
        self._write_file(
            temp_dir / "pyproject.toml",
            "[project]\nname='serverless-demo'\ndependencies=['functions-framework>=3.0']\n",
        )

        report = _analyze_project(temp_dir, None)
        hotspot = self._top_hotspot(report)
        self.assertEqual(report.profile.primary_profile, "serverless_application")
        self.assertIn("functions\\main.py", hotspot["file"])
        self.assertEqual(hotspot["function"], "boot_handler")

    def test_stage2_relevance_firmware_cloud_surfaces_both_sides(self) -> None:
        temp_dir = self._scratch_dir("stage2_firmware_cloud")
        self._write_file(
            temp_dir / "firmware" / "drivers" / "sensor.c",
            "int read_sensor(int* items, int count) {\n"
            "    int total = 0;\n"
            "    for (int i = 0; i < count; ++i) {\n"
            "        for (int j = 0; j < count; ++j) {\n"
            "            if (items[i] == items[j]) {\n"
            "                total += 1;\n"
            "            }\n"
            "        }\n"
            "    }\n"
            "    return total;\n"
            "}\n",
        )
        self._write_file(
            temp_dir / "cloud" / "api" / "app.py",
            "def handle_request(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "pyproject.toml",
            "[project]\nname='hybrid-demo'\ndependencies=['fastapi>=1.0']\n",
        )
        self._write_file(
            temp_dir / "platformio.ini",
            "[env:demo]\nplatform = espressif32\nframework = arduino\n",
        )

        report = _analyze_project(temp_dir, None)
        hotspots = report.summary.prioritized_hotspots or report.summary.top_functions
        top_files = {item["file"] for item in hotspots[:2]}
        self.assertEqual(report.profile.hybrid_shape, "device_firmware_cloud")
        self.assertTrue(any(file.endswith("firmware\\drivers\\sensor.c") for file in top_files))
        self.assertTrue(any(file.endswith("cloud\\api\\app.py") for file in top_files))

    def test_stage2_relevance_microservices_prefers_service_entrypoints(self) -> None:
        temp_dir = self._scratch_dir("stage2_microservices")
        self._write_file(
            temp_dir / "services" / "auth" / "main.py",
            "def handle_request(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "services" / "billing" / "server.py",
            "def process_billing(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "tests" / "test_gateway.py",
            "def test_gateway(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "pyproject.toml",
            "[project]\nname='micro-demo'\ndependencies=['fastapi>=1.0']\n",
        )

        report = _analyze_project(temp_dir, None)
        hotspot = self._top_hotspot(report)
        self.assertEqual(report.profile.service_topology, "microservices")
        self.assertNotIn("tests\\test_gateway.py", hotspot["file"])
        self.assertIn(hotspot["project_priority_label"], {"worth_reviewing", "high_priority", "fix_first"})

    def test_stage2_relevance_test_heavy_repository_stays_discounted(self) -> None:
        temp_dir = self._scratch_dir("stage2_test_heavy")
        self._write_file(
            temp_dir / "tests" / "test_worker.py",
            "def test_worker(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "docs" / "example.py",
            "def docs_example(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )

        report = _analyze_project(temp_dir, None)
        hotspot = self._top_hotspot(report)
        self.assertEqual(report.profile.primary_profile, "test_heavy_repository")
        self.assertGreater(report.summary.discounted_functions, 0)
        self.assertIn(hotspot["project_priority_label"], {"ignore_for_now", "watch", "worth_reviewing"})
        self.assertIn("relevance", format_json_report(report)["files"][0]["functions"][0])

    def test_stage3_synthesis_framework_library_groups_dispatch_and_noise(self) -> None:
        temp_dir = self._scratch_dir("stage3_framework_library")
        self._write_file(
            temp_dir / "src" / "dispatch.py",
            "def dispatch_request(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "tests" / "test_extensions.py",
            "def test_dispatch_request(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "docs" / "example.py",
            "def docs_dispatch_example(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "pyproject.toml",
            "[project]\nname='framework-demo'\ndependencies=['flask>=3.0']\n",
        )

        report = _analyze_project(temp_dir, None)
        synthesis = self._synthesis(report)
        self.assertEqual(report.profile.primary_profile, "framework_library")
        self.assertTrue(any(key.startswith("dispatch_complexity_review:") for key in self._theme_keys(report)))
        self.assertEqual(synthesis.action_lanes[0].key, "dispatch_complexity_review")
        self.assertIn("tests", synthesis.noise_diagnostic.dominant_noise_zones)

    def test_stage3_synthesis_api_service_separates_request_and_startup(self) -> None:
        temp_dir = self._scratch_dir("stage3_api_service")
        self._write_file(
            temp_dir / "api" / "handlers.py",
            "def handle_request(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "app.py",
            "def boot_service(items):\n"
            "    values = []\n"
            "    for item in items:\n"
            "        values.append(str(item))\n"
            "    return ''.join(values)\n",
        )
        self._write_file(
            temp_dir / "pyproject.toml",
            "[project]\nname='api-demo'\ndependencies=['fastapi>=1.0','uvicorn>=0.1']\n",
        )

        report = _analyze_project(temp_dir, None)
        self.assertEqual(report.profile.web_shape, "api_service")
        self.assertTrue(any(key.startswith("request_path_hotspots:") for key in self._theme_keys(report)))
        self.assertIn("startup_path_cleanup", self._lane_keys(report))
        self.assertEqual(self._synthesis(report).action_lanes[0].key, "request_path_hotspots")

    def test_stage3_synthesis_website_surfaces_frontend_theme(self) -> None:
        temp_dir = self._scratch_dir("stage3_website")
        self._write_file(
            temp_dir / "pages" / "home.ts",
            "export function render_page(items: number[], lookup: number[]) {\n"
            "  let total = 0;\n"
            "  for (const item of items) {\n"
            "    for (const other of lookup) {\n"
            "      if (item === other) {\n"
            "        total += 1;\n"
            "      }\n"
            "    }\n"
            "  }\n"
            "  return total;\n"
            "}\n",
        )
        self._write_file(
            temp_dir / "docs" / "example.ts",
            "export function docs_example(items: number[], lookup: number[]) {\n"
            "  let total = 0;\n"
            "  for (const item of items) {\n"
            "    for (const other of lookup) {\n"
            "      if (item === other) {\n"
            "        total += 1;\n"
            "      }\n"
            "    }\n"
            "  }\n"
            "  return total;\n"
            "}\n",
        )
        self._write_file(
            temp_dir / "package.json",
            json.dumps({"name": "webapp-demo", "dependencies": {"react": "^18.0.0", "next": "^14.0.0"}}),
        )

        report = _analyze_project(temp_dir, None)
        self.assertEqual(report.profile.web_shape, "website_web_app")
        self.assertEqual(self._synthesis(report).action_lanes[0].key, "frontend_responsiveness")
        self.assertTrue(any(key.startswith("frontend_responsiveness:") for key in self._theme_keys(report)))

    def test_stage3_synthesis_cli_surfaces_command_dispatch_lane(self) -> None:
        temp_dir = self._scratch_dir("stage3_cli")
        self._write_file(
            temp_dir / "cli" / "main.py",
            "def main(items):\n"
            "    values = []\n"
            "    for item in items:\n"
            "        values.append(str(item))\n"
            "    return ''.join(values)\n",
        )
        self._write_file(
            temp_dir / "helpers" / "strings.py",
            "def helper(items):\n"
            "    values = []\n"
            "    for item in items:\n"
            "        values.append(str(item))\n"
            "    return ''.join(values)\n",
        )
        self._write_file(
            temp_dir / "pyproject.toml",
            "[project]\nname='cli-demo'\ndependencies=['click>=8.0']\n",
        )

        report = _analyze_project(temp_dir, None)
        self.assertEqual(report.profile.primary_profile, "cli_tool")
        self.assertEqual(self._synthesis(report).action_lanes[0].key, "command_dispatch_cleanup")

    def test_stage3_synthesis_data_pipeline_groups_throughput(self) -> None:
        temp_dir = self._scratch_dir("stage3_data_pipeline")
        self._write_file(
            temp_dir / "pipelines" / "daily.py",
            "def run_pipeline(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "jobs" / "worker.py",
            "def process_batch(items):\n"
            "    values = []\n"
            "    for item in items:\n"
            "        values.append(str(item))\n"
            "    return ''.join(values)\n",
        )
        self._write_file(
            temp_dir / "pyproject.toml",
            "[project]\nname='pipeline-demo'\ndependencies=['airflow>=2.0','pandas>=2.0']\n",
        )

        report = _analyze_project(temp_dir, None)
        self.assertEqual(report.profile.primary_profile, "data_pipeline")
        self.assertEqual(self._synthesis(report).action_lanes[0].key, "pipeline_throughput_fixes")

    def test_stage3_synthesis_serverless_splits_startup_and_handler(self) -> None:
        temp_dir = self._scratch_dir("stage3_serverless")
        self._write_file(
            temp_dir / "functions" / "main.py",
            "def boot_handler(items):\n"
            "    values = []\n"
            "    for item in items:\n"
            "        values.append(str(item))\n"
            "    return ''.join(values)\n",
        )
        self._write_file(
            temp_dir / "functions" / "request.py",
            "def handle_request(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "pyproject.toml",
            "[project]\nname='serverless-demo'\ndependencies=['functions-framework>=3.0']\n",
        )

        report = _analyze_project(temp_dir, None)
        lane_keys = self._lane_keys(report)
        self.assertEqual(report.profile.primary_profile, "serverless_application")
        self.assertIn("startup_path_cleanup", lane_keys)
        self.assertIn("request_path_hotspots", lane_keys)

    def test_stage3_synthesis_mobile_surfaces_mobile_lane(self) -> None:
        temp_dir = self._scratch_dir("stage3_mobile")
        self._write_file(
            temp_dir / "mobile" / "poller.ts",
            "export function poll_updates(items: number[], lookup: number[]) {\n"
            "  let total = 0;\n"
            "  for (const item of items) {\n"
            "    for (const other of lookup) {\n"
            "      if (item === other) {\n"
            "        total += 1;\n"
            "      }\n"
            "    }\n"
            "  }\n"
            "  return total;\n"
            "}\n",
        )
        self._write_file(
            temp_dir / "package.json",
            json.dumps({"name": "mobile-demo", "dependencies": {"react-native": "^0.76.0"}}),
        )

        report = _analyze_project(temp_dir, None)
        self.assertEqual(report.profile.primary_profile, "mobile_application")
        self.assertEqual(self._synthesis(report).action_lanes[0].key, "mobile_app_efficiency")

    def test_stage3_synthesis_firmware_cloud_produces_dual_lanes(self) -> None:
        temp_dir = self._scratch_dir("stage3_firmware_cloud")
        self._write_file(
            temp_dir / "firmware" / "drivers" / "sensor.c",
            "int read_sensor(int* items, int count) {\n"
            "    int total = 0;\n"
            "    for (int i = 0; i < count; ++i) {\n"
            "        for (int j = 0; j < count; ++j) {\n"
            "            if (items[i] == items[j]) {\n"
            "                total += 1;\n"
            "            }\n"
            "        }\n"
            "    }\n"
            "    return total;\n"
            "}\n",
        )
        self._write_file(
            temp_dir / "cloud" / "api" / "app.py",
            "def handle_request(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "pyproject.toml",
            "[project]\nname='hybrid-demo'\ndependencies=['fastapi>=1.0']\n",
        )
        self._write_file(
            temp_dir / "platformio.ini",
            "[env:demo]\nplatform = espressif32\nframework = arduino\n",
        )

        report = _analyze_project(temp_dir, None)
        lane_keys = self._lane_keys(report)
        self.assertEqual(report.profile.hybrid_shape, "device_firmware_cloud")
        self.assertIn("device_memory_pressure", lane_keys)
        self.assertIn("cloud_control_path", lane_keys)

    def test_stage3_synthesis_microservices_favors_service_entrypoints(self) -> None:
        temp_dir = self._scratch_dir("stage3_microservices")
        self._write_file(
            temp_dir / "services" / "auth" / "main.py",
            "def handle_request(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "services" / "billing" / "server.py",
            "def process_billing(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "gateway" / "router.py",
            "def route_request(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "tests" / "test_gateway.py",
            "def test_gateway(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "pyproject.toml",
            "[project]\nname='micro-demo'\ndependencies=['fastapi>=1.0']\n",
        )

        report = _analyze_project(temp_dir, None)
        self.assertEqual(report.profile.service_topology, "microservices")
        self.assertEqual(self._synthesis(report).action_lanes[0].key, "service_entrypoint_review")

    def test_stage3_synthesis_test_heavy_repo_reports_noise_pressure(self) -> None:
        temp_dir = self._scratch_dir("stage3_test_heavy")
        self._write_file(
            temp_dir / "tests" / "test_worker.py",
            "def test_worker(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "docs" / "example.py",
            "def docs_example(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )

        report = _analyze_project(temp_dir, None)
        synthesis = self._synthesis(report)
        self.assertEqual(report.profile.primary_profile, "test_heavy_repository")
        self.assertEqual(synthesis.action_lanes[0].key, "noise_cleanup_only")
        self.assertGreaterEqual(synthesis.noise_diagnostic.noise_ratio, 0.5)
        self.assertIn("noise-heavy", synthesis.noise_diagnostic.summary)

    def test_stage3_outputs_expose_synthesis_in_json_and_text(self) -> None:
        temp_dir = self._scratch_dir("stage3_output_shape")
        self._write_file(
            temp_dir / "api" / "handlers.py",
            "def handle_request(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "app.py",
            "def boot_service(items):\n"
            "    values = []\n"
            "    for item in items:\n"
            "        values.append(str(item))\n"
            "    return ''.join(values)\n",
        )
        self._write_file(
            temp_dir / "pyproject.toml",
            "[project]\nname='api-demo'\ndependencies=['fastapi>=1.0','uvicorn>=0.1']\n",
        )

        report = _analyze_project(temp_dir, None)
        payload = format_json_report(report)
        text = format_text_report(report)
        self.assertIn("synthesis", payload)
        self.assertIn("repository_story", payload["synthesis"])
        self.assertTrue(payload["synthesis"]["dominant_themes"])
        self.assertIn("=== Stage 3 Synthesis ===", text)
        self.assertIn("Repository story:", text)
        self.assertIn("Action Lanes:", text)

    def test_stage3_mixed_repo_lane_assignment_stays_file_local(self) -> None:
        temp_dir = self._scratch_dir("stage3_mixed_repo_lane_locality")
        self._write_file(
            temp_dir / "firmware" / "drivers" / "sensor.c",
            "int read_sensor(int* items, int count) {\n"
            "    int total = 0;\n"
            "    for (int i = 0; i < count; ++i) {\n"
            "        for (int j = 0; j < count; ++j) {\n"
            "            if (items[i] == items[j]) {\n"
            "                total += 1;\n"
            "            }\n"
            "        }\n"
            "    }\n"
            "    return total;\n"
            "}\n",
        )
        self._write_file(
            temp_dir / "cloud" / "api" / "app.py",
            "def handle_request(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "src" / "helpers.py",
            "def compute_pairs(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "pyproject.toml",
            "[project]\nname='hybrid-demo'\ndependencies=['fastapi>=1.0']\n",
        )
        self._write_file(
            temp_dir / "platformio.ini",
            "[env:demo]\nplatform = espressif32\nframework = arduino\n",
        )

        report = _analyze_project(temp_dir, None)
        self.assertIn("device_memory_pressure:loop_amplification", self._theme_keys_for_file(report, "firmware\\drivers\\sensor.c"))
        self.assertIn("cloud_control_path:loop_amplification", self._theme_keys_for_file(report, "cloud\\api\\app.py"))
        self.assertIn("general_efficiency_review:loop_amplification", self._theme_keys_for_file(report, "src\\helpers.py"))
        self.assertNotIn("device_memory_pressure:loop_amplification", self._theme_keys_for_file(report, "src\\helpers.py"))
        self.assertNotIn("request_path_hotspots:loop_amplification", self._theme_keys_for_file(report, "src\\helpers.py"))

    def test_stage4_multilens_framework_library_defaults_to_maintainability(self) -> None:
        temp_dir = self._scratch_dir("stage4_framework_library")
        self._write_file(
            temp_dir / "src" / "dispatch.py",
            "def dispatch_request(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "tests" / "test_dispatch.py",
            "def test_dispatch_request(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "docs" / "example.py",
            "def docs_dispatch_example(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "pyproject.toml",
            "[project]\nname='framework-demo'\ndependencies=['flask>=3.0']\n",
        )

        report = _analyze_project(temp_dir, None)
        multi_lens = self._multi_lens(report)
        default_report = self._lens_report(report)
        self.assertEqual(multi_lens.default_lens, "maintainability")
        self.assertIn("api_stability", multi_lens.available_lenses)
        self.assertEqual(default_report.top_lanes[0].lane_key, "dispatch_complexity_review")
        self.assertTrue(any(theme.theme_key.startswith("dispatch_complexity_review:") for theme in default_report.top_themes))

    def test_stage4_multilens_api_stability_reorders_framework_library_view(self) -> None:
        temp_dir = self._scratch_dir("stage4_api_stability_framework")
        self._write_file(
            temp_dir / "src" / "dispatch.py",
            "def dispatch_request(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "api" / "handlers.py",
            "def handle_request(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "tests" / "test_dispatch.py",
            "def test_dispatch_request(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "docs" / "example.py",
            "def docs_dispatch_example(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "pyproject.toml",
            "[project]\nname='framework-demo'\ndependencies=['flask>=3.0']\n",
        )

        report = _analyze_project(temp_dir, None)
        multi_lens = self._multi_lens(report)
        default_report = self._lens_report(report)
        api_stability_report = self._lens_report(report, "api_stability")

        self.assertEqual(report.profile.primary_profile, "framework_library")
        self.assertEqual(multi_lens.default_lens, "maintainability")
        self.assertIn("api_stability", multi_lens.available_lenses)
        self.assertEqual(default_report.top_lanes[0].lane_key, "dispatch_complexity_review")
        self.assertEqual(api_stability_report.top_lanes[0].lane_key, "request_path_hotspots")
        self.assertNotEqual(default_report.top_lanes[0].lane_key, api_stability_report.top_lanes[0].lane_key)

    def test_stage4_multilens_api_service_defaults_to_performance(self) -> None:
        temp_dir = self._scratch_dir("stage4_api_service")
        self._write_file(
            temp_dir / "api" / "handlers.py",
            "def handle_request(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "app.py",
            "def boot_service(items):\n"
            "    values = []\n"
            "    for item in items:\n"
            "        values.append(str(item))\n"
            "    return ''.join(values)\n",
        )
        self._write_file(
            temp_dir / "pyproject.toml",
            "[project]\nname='api-demo'\ndependencies=['fastapi>=1.0','uvicorn>=0.1']\n",
        )

        report = _analyze_project(temp_dir, None)
        multi_lens = self._multi_lens(report)
        default_report = self._lens_report(report)
        self.assertEqual(multi_lens.default_lens, "performance")
        self.assertEqual(default_report.top_lanes[0].lane_key, "request_path_hotspots")
        self.assertIn("cloud_cost", multi_lens.available_lenses)

    def test_stage4_multilens_website_defaults_to_performance(self) -> None:
        temp_dir = self._scratch_dir("stage4_website")
        self._write_file(
            temp_dir / "pages" / "home.ts",
            "export function render_page(items: number[], lookup: number[]) {\n"
            "  let total = 0;\n"
            "  for (const item of items) {\n"
            "    for (const other of lookup) {\n"
            "      if (item === other) {\n"
            "        total += 1;\n"
            "      }\n"
            "    }\n"
            "  }\n"
            "  return total;\n"
            "}\n",
        )
        self._write_file(
            temp_dir / "package.json",
            json.dumps({"name": "webapp-demo", "dependencies": {"react": "^18.0.0", "next": "^14.0.0"}}),
        )

        report = _analyze_project(temp_dir, None)
        multi_lens = self._multi_lens(report)
        default_report = self._lens_report(report)
        self.assertEqual(multi_lens.default_lens, "performance")
        self.assertEqual(default_report.top_lanes[0].lane_key, "frontend_responsiveness")

    def test_stage4_multilens_cli_defaults_to_startup(self) -> None:
        temp_dir = self._scratch_dir("stage4_cli")
        self._write_file(
            temp_dir / "cli" / "main.py",
            "def main(items):\n"
            "    values = []\n"
            "    for item in items:\n"
            "        values.append(str(item))\n"
            "    return ''.join(values)\n",
        )
        self._write_file(
            temp_dir / "helpers" / "strings.py",
            "def helper(items):\n"
            "    values = []\n"
            "    for item in items:\n"
            "        values.append(str(item))\n"
            "    return ''.join(values)\n",
        )
        self._write_file(
            temp_dir / "pyproject.toml",
            "[project]\nname='cli-demo'\ndependencies=['click>=8.0']\n",
        )

        report = _analyze_project(temp_dir, None)
        multi_lens = self._multi_lens(report)
        default_report = self._lens_report(report)
        self.assertEqual(multi_lens.default_lens, "startup")
        self.assertEqual(default_report.top_lanes[0].lane_key, "command_dispatch_cleanup")

    def test_stage4_multilens_data_pipeline_defaults_to_performance(self) -> None:
        temp_dir = self._scratch_dir("stage4_data_pipeline")
        self._write_file(
            temp_dir / "pipelines" / "daily.py",
            "def run_pipeline(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "jobs" / "worker.py",
            "def process_batch(items):\n"
            "    values = []\n"
            "    for item in items:\n"
            "        values.append(str(item))\n"
            "    return ''.join(values)\n",
        )
        self._write_file(
            temp_dir / "pyproject.toml",
            "[project]\nname='pipeline-demo'\ndependencies=['airflow>=2.0','pandas>=2.0']\n",
        )

        report = _analyze_project(temp_dir, None)
        multi_lens = self._multi_lens(report)
        default_report = self._lens_report(report)
        self.assertEqual(multi_lens.default_lens, "performance")
        self.assertEqual(default_report.top_lanes[0].lane_key, "pipeline_throughput_fixes")

    def test_stage4_multilens_serverless_reorders_between_startup_and_performance(self) -> None:
        temp_dir = self._scratch_dir("stage4_serverless")
        self._write_file(
            temp_dir / "functions" / "main.py",
            "def boot_handler(items):\n"
            "    values = []\n"
            "    for item in items:\n"
            "        values.append(str(item))\n"
            "    return ''.join(values)\n",
        )
        self._write_file(
            temp_dir / "functions" / "request.py",
            "def handle_request(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "pyproject.toml",
            "[project]\nname='serverless-demo'\ndependencies=['functions-framework>=3.0']\n",
        )

        report = _analyze_project(temp_dir, None)
        multi_lens = self._multi_lens(report)
        default_report = self._lens_report(report)
        performance_report = self._lens_report(report, "performance")
        self.assertEqual(multi_lens.default_lens, "startup")
        self.assertEqual(default_report.top_lanes[0].lane_key, "startup_path_cleanup")
        self.assertEqual(performance_report.top_lanes[0].lane_key, "request_path_hotspots")
        self.assertNotEqual(default_report.top_lanes[0].lane_key, performance_report.top_lanes[0].lane_key)

    def test_stage4_multilens_mobile_defaults_to_battery(self) -> None:
        temp_dir = self._scratch_dir("stage4_mobile")
        self._write_file(
            temp_dir / "mobile" / "poller.ts",
            "export function poll_updates(items: number[], lookup: number[]) {\n"
            "  let total = 0;\n"
            "  for (const item of items) {\n"
            "    for (const other of lookup) {\n"
            "      if (item === other) {\n"
            "        total += 1;\n"
            "      }\n"
            "    }\n"
            "  }\n"
            "  return total;\n"
            "}\n",
        )
        self._write_file(
            temp_dir / "package.json",
            json.dumps({"name": "mobile-demo", "dependencies": {"react-native": "^0.76.0"}}),
        )

        report = _analyze_project(temp_dir, None)
        multi_lens = self._multi_lens(report)
        default_report = self._lens_report(report)
        self.assertEqual(multi_lens.default_lens, "battery")
        self.assertEqual(default_report.top_lanes[0].lane_key, "mobile_app_efficiency")

    def test_stage4_multilens_firmware_cloud_shifts_for_cloud_cost(self) -> None:
        temp_dir = self._scratch_dir("stage4_firmware_cloud")
        self._write_file(
            temp_dir / "firmware" / "drivers" / "sensor.c",
            "int read_sensor(int* items, int count) {\n"
            "    int total = 0;\n"
            "    for (int i = 0; i < count; ++i) {\n"
            "        for (int j = 0; j < count; ++j) {\n"
            "            if (items[i] == items[j]) {\n"
            "                total += 1;\n"
            "            }\n"
            "        }\n"
            "    }\n"
            "    return total;\n"
            "}\n",
        )
        self._write_file(
            temp_dir / "cloud" / "api" / "app.py",
            "def handle_request(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "pyproject.toml",
            "[project]\nname='hybrid-demo'\ndependencies=['fastapi>=1.0']\n",
        )
        self._write_file(
            temp_dir / "platformio.ini",
            "[env:demo]\nplatform = espressif32\nframework = arduino\n",
        )

        report = _analyze_project(temp_dir, None)
        multi_lens = self._multi_lens(report)
        default_report = self._lens_report(report)
        cloud_cost_report = self._lens_report(report, "cloud_cost")
        self.assertEqual(multi_lens.default_lens, "reliability")
        self.assertEqual(default_report.top_lanes[0].lane_key, "device_memory_pressure")
        self.assertEqual(cloud_cost_report.top_lanes[0].lane_key, "cloud_control_path")

    def test_stage4_multilens_microservices_defaults_to_performance(self) -> None:
        temp_dir = self._scratch_dir("stage4_microservices")
        self._write_file(
            temp_dir / "services" / "auth" / "main.py",
            "def handle_request(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "services" / "billing" / "server.py",
            "def process_billing(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "gateway" / "router.py",
            "def route_request(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "pyproject.toml",
            "[project]\nname='micro-demo'\ndependencies=['fastapi>=1.0']\n",
        )

        report = _analyze_project(temp_dir, None)
        multi_lens = self._multi_lens(report)
        default_report = self._lens_report(report)
        self.assertEqual(multi_lens.default_lens, "performance")
        self.assertEqual(default_report.top_lanes[0].lane_key, "service_entrypoint_review")

    def test_stage4_multilens_test_heavy_repo_keeps_noise_guardrails(self) -> None:
        temp_dir = self._scratch_dir("stage4_test_heavy")
        self._write_file(
            temp_dir / "tests" / "test_worker.py",
            "def test_worker(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "docs" / "example.py",
            "def docs_example(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )

        report = _analyze_project(temp_dir, None)
        multi_lens = self._multi_lens(report)
        default_report = self._lens_report(report)
        self.assertEqual(multi_lens.default_lens, "maintainability")
        self.assertEqual(default_report.top_lanes[0].lane_key, "noise_cleanup_only")
        self.assertGreaterEqual(self._synthesis(report).noise_diagnostic.noise_ratio, 0.5)

    def test_stage4_outputs_expose_default_lens_in_json_text_and_terminal(self) -> None:
        temp_dir = self._scratch_dir("stage4_output_shape")
        self._write_file(
            temp_dir / "api" / "handlers.py",
            "def handle_request(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "app.py",
            "def boot_service(items):\n"
            "    values = []\n"
            "    for item in items:\n"
            "        values.append(str(item))\n"
            "    return ''.join(values)\n",
        )
        self._write_file(
            temp_dir / "pyproject.toml",
            "[project]\nname='api-demo'\ndependencies=['fastapi>=1.0','uvicorn>=0.1']\n",
        )

        report = _analyze_project(temp_dir, None)
        payload = format_json_report(report)
        text = format_text_report(report)
        buffer = StringIO()
        original_console = terminal_formatter.console
        terminal_formatter.console = Console(file=buffer, force_terminal=False, color_system=None, width=120)
        try:
            terminal_formatter.print_terminal_report(report)
        finally:
            terminal_formatter.console = original_console
        terminal_output = buffer.getvalue()

        self.assertIn("multi_lens", payload)
        self.assertEqual(payload["multi_lens"]["default_lens"], report.multi_lens.default_lens)
        self.assertTrue(payload["multi_lens"]["reports"][0]["top_themes"])
        self.assertIn("=== Stage 4 Multi-Lens ===", text)
        self.assertIn("Default lens", text)
        self.assertIn("Top Themes For Default Lens:", text)
        self.assertIn("Top Lanes For Default Lens:", text)
        self.assertIn("Stage 4 Multi-Lens", terminal_output)
        self.assertIn("Default lens", terminal_output)
        self.assertIn("Top Themes", terminal_output)

    def test_stage5_payload_builder_enforces_compression_caps(self) -> None:
        profile, summary, synthesis, multi_lens = self._stage5_contract_fixture()

        payload, budget = build_ai_overlay_payload(profile, summary, synthesis, multi_lens)

        self.assertEqual(budget.max_top_themes, AI_OVERLAY_MAX_TOP_THEMES)
        self.assertEqual(budget.max_top_lanes, AI_OVERLAY_MAX_TOP_LANES)
        self.assertEqual(budget.max_top_hotspots, AI_OVERLAY_MAX_TOP_HOTSPOTS)
        self.assertEqual(budget.max_examples_per_theme, AI_OVERLAY_MAX_EXAMPLES_PER_THEME)
        self.assertEqual(len(payload.top_themes), AI_OVERLAY_MAX_TOP_THEMES)
        self.assertEqual(len(payload.top_lanes), AI_OVERLAY_MAX_TOP_LANES)
        self.assertEqual(len(payload.top_hotspots), AI_OVERLAY_MAX_TOP_HOTSPOTS)
        self.assertTrue(all(len(theme["representative_examples"]) <= AI_OVERLAY_MAX_EXAMPLES_PER_THEME for theme in payload.top_themes))
        self.assertNotIn("zone_classification", payload.project_profile)

    def test_stage5_ai_overlay_off_mode_skips_provider_calls(self) -> None:
        temp_dir = self._scratch_dir("stage5_off_mode")
        self._write_file(
            temp_dir / "api" / "handlers.py",
            "def handle_request(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "pyproject.toml",
            "[project]\nname='stage5-off'\ndependencies=['fastapi>=1.0']\n",
        )
        provider = StubAIOverlayProvider(response={})

        report = _analyze_project(temp_dir, None, ai_mode="off", ai_provider=provider)

        self.assertIsNotNone(report.ai_overlay)
        self.assertFalse(report.ai_overlay.enabled)
        self.assertEqual(report.ai_overlay.status, "disabled")
        self.assertEqual(provider.calls, [])

    def test_stage5_ai_overlay_assist_mode_wires_bounded_payload_and_default_model(self) -> None:
        temp_dir = self._scratch_dir("stage5_assist_mode")
        self._write_file(
            temp_dir / "api" / "handlers.py",
            "def handle_request(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "app.py",
            "def boot_service(items):\n"
            "    values = []\n"
            "    for item in items:\n"
            "        values.append(str(item))\n"
            "    return ''.join(values)\n",
        )
        self._write_file(
            temp_dir / "pyproject.toml",
            "[project]\nname='stage5-assist'\ndependencies=['fastapi>=1.0','uvicorn>=0.1']\n",
        )
        provider = StubAIOverlayProvider(
            response={
                "executive_summary": "The bounded deterministic payload points to request-path pressure first.",
                "maintainer_plan": [
                    "Start with the top deterministic request-path lane.",
                    "Validate the highest-priority hotspot in production code.",
                    "Use the deterministic lens ordering to batch the next fixes.",
                ],
                "lens_explanation": "The deterministic performance lens stays first because the repo looks request-response heavy.",
                "grounded_theme_keys": [],
                "grounded_lane_keys": [],
                "grounded_hotspots": [],
                "caveats": ["No new findings were introduced."],
            }
        )

        report = _analyze_project(temp_dir, None, ai_mode="assist", ai_provider=provider)

        self.assertEqual(report.ai_overlay.status, "completed")
        self.assertEqual(report.ai_overlay.mode, "assist")
        self.assertEqual(report.ai_overlay.model, AI_OVERLAY_DEFAULT_ASSIST_MODEL)
        self.assertEqual(len(provider.calls), 1)
        self.assertEqual(provider.calls[0]["mode"], "assist")
        self.assertEqual(provider.calls[0]["model"], AI_OVERLAY_DEFAULT_ASSIST_MODEL)
        self.assertLessEqual(len(provider.calls[0]["payload"].top_themes), AI_OVERLAY_MAX_TOP_THEMES)
        self.assertLessEqual(len(provider.calls[0]["payload"].top_lanes), AI_OVERLAY_MAX_TOP_LANES)
        self.assertLessEqual(len(provider.calls[0]["payload"].top_hotspots), AI_OVERLAY_MAX_TOP_HOTSPOTS)
        self.assertTrue(report.ai_overlay.result.grounded_theme_keys)
        self.assertTrue(report.ai_overlay.result.grounded_lane_keys)
        self.assertTrue(report.ai_overlay.result.grounded_hotspots)

    def test_stage5_ai_overlay_failure_does_not_break_deterministic_report(self) -> None:
        temp_dir = self._scratch_dir("stage5_failure_safe")
        self._write_file(
            temp_dir / "api" / "handlers.py",
            "def handle_request(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "pyproject.toml",
            "[project]\nname='stage5-failure'\ndependencies=['fastapi>=1.0']\n",
        )
        provider = StubAIOverlayProvider(error=RuntimeError("overlay backend unavailable"))

        report = _analyze_project(temp_dir, None, ai_mode="assist", ai_provider=provider)
        text = format_text_report(report)

        self.assertEqual(report.ai_overlay.status, "failed")
        self.assertTrue(report.summary.why_it_matters)
        self.assertTrue(report.summary.recommended_next_step)
        self.assertIn("AI overlay unavailable; deterministic report completed successfully.", report.ai_overlay.notes)
        self.assertIn("=== Stage 5 AI Overlay ===", text)
        self.assertIn("AI overlay unavailable; deterministic report completed successfully.", text)

    def test_stage5_ai_overlay_grounding_filters_invalid_references_and_separates_outputs(self) -> None:
        temp_dir = self._scratch_dir("stage5_grounding")
        self._write_file(
            temp_dir / "api" / "handlers.py",
            "def handle_request(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "app.py",
            "def boot_service(items):\n"
            "    values = []\n"
            "    for item in items:\n"
            "        values.append(str(item))\n"
            "    return ''.join(values)\n",
        )
        self._write_file(
            temp_dir / "pyproject.toml",
            "[project]\nname='stage5-grounding'\ndependencies=['fastapi>=1.0','uvicorn>=0.1']\n",
        )
        provider = GroundingDriftProvider()

        report = _analyze_project(temp_dir, None, ai_mode="assist", ai_provider=provider)
        payload = format_json_report(report)
        text = format_text_report(report)
        buffer = StringIO()
        original_console = terminal_formatter.console
        terminal_formatter.console = Console(file=buffer, force_terminal=False, color_system=None, width=120)
        try:
            terminal_formatter.print_terminal_report(report)
        finally:
            terminal_formatter.console = original_console
        terminal_output = buffer.getvalue()

        self.assertEqual(report.ai_overlay.status, "completed")
        self.assertNotIn("invented-theme", report.ai_overlay.result.grounded_theme_keys)
        self.assertNotIn("invented-lane", report.ai_overlay.result.grounded_lane_keys)
        self.assertTrue(
            all(item["file"] != "invented.py" for item in report.ai_overlay.result.grounded_hotspots)
        )
        self.assertIn("ai_overlay", payload)
        self.assertEqual(payload["ai_overlay"]["status"], "completed")
        self.assertIn("grounded_theme_keys", payload["ai_overlay"]["result"])
        self.assertIn("=== Stage 5 AI Overlay ===", text)
        self.assertIn("AI Executive Summary:", text)
        self.assertIn("Stage 5 AI Overlay", terminal_output)
        self.assertIn("AI Executive Summary", terminal_output)

    def test_stage5_ai_overlay_interactive_mode_is_scaffolded(self) -> None:
        temp_dir = self._scratch_dir("stage5_interactive")
        self._write_file(
            temp_dir / "api" / "handlers.py",
            "def handle_request(items, lookup):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        for other in lookup:\n"
            "            if item == other:\n"
            "                total += 1\n"
            "    return total\n",
        )
        self._write_file(
            temp_dir / "pyproject.toml",
            "[project]\nname='stage5-interactive'\ndependencies=['fastapi>=1.0']\n",
        )
        provider = StubAIOverlayProvider(response={})

        report = _analyze_project(temp_dir, None, ai_mode="interactive", ai_provider=provider)

        self.assertEqual(report.ai_overlay.status, "scaffolded")
        self.assertEqual(report.ai_overlay.provider, "scaffold")
        self.assertEqual(provider.calls, [])
        self.assertTrue(report.ai_overlay.notes)

    def test_file_text_output_uses_raw_cost_and_keeps_urgency_visible(self) -> None:
        temp_dir = self._scratch_dir("stage3_file_text_cost_label")
        sample_file = temp_dir / "service.py"
        self._write_file(
            sample_file,
            "def setup_cache(items):\n"
            "    values = []\n"
            "    for item in items:\n"
            "        values.append(item)\n"
            "    return values\n",
        )

        report = _analyze_file(sample_file, None, None)
        text = format_text_report(report)
        self.assertEqual(report.functions[0].cost.label, "MODERATE")
        self.assertEqual(report.functions[0].context.adjusted_label, "CHEAP")
        self.assertIn("Cost     : MODERATE", text)
        self.assertIn("Urgency: CHEAP - modifier downgrade", text)
        self.assertNotIn("Cost     : CHEAP", text)

    def test_file_terminal_output_uses_raw_cost_and_keeps_urgency_visible(self) -> None:
        temp_dir = self._scratch_dir("stage3_file_terminal_cost_label")
        sample_file = temp_dir / "service.py"
        self._write_file(
            sample_file,
            "def setup_cache(items):\n"
            "    values = []\n"
            "    for item in items:\n"
            "        values.append(item)\n"
            "    return values\n",
        )

        report = _analyze_file(sample_file, None, None)
        buffer = StringIO()
        original_console = terminal_formatter.console
        terminal_formatter.console = Console(file=buffer, force_terminal=False, color_system=None, width=120)
        try:
            terminal_formatter.print_terminal_report(report)
        finally:
            terminal_formatter.console = original_console
        output = buffer.getvalue()

        self.assertIn("Cost     : MODERATE", output)
        self.assertIn("Urgency: CHEAP - modifier downgrade", output)
        self.assertNotIn("Cost     : CHEAP", output)

    def test_doctor_report_shape(self) -> None:
        report = build_doctor_report()
        self.assertIn(report.overall_status, {"READY", "READY_WITH_AUTO_BOOTSTRAP", "DEGRADED"})
        self.assertIn(report.mode, {"native", "native-auto-bootstrap", "degraded"})
        self.assertIsInstance(report.providers, list)
        self.assertGreaterEqual(len(report.next_steps), 1)

    def test_output_json_file(self) -> None:
        output_path = self._scratch_dir("output_json_file") / "report.json"
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
        output_path = self._scratch_dir("output_text_file") / "report.txt"
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

    def test_output_directory_error_is_user_friendly(self) -> None:
        output_path = ROOT / "tests" / "artifacts"
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
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Solvix: Cannot write report to", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
