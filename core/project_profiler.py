"""Deterministic project profiling for Stage 1 repository intelligence."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import tomllib

from core.language_detector import detect_language
from core.report import (
    ConfidenceFactor,
    DependencyEvidenceItem,
    FileZoneClassification,
    ProfileEvidence,
    ProjectProfile,
)

NOISE_ZONE_NAMES = {
    "test",
    "tests",
    "testing",
    "spec",
    "specs",
    "fixtures",
    "examples",
    "example",
    "docs",
    "doc",
    "benchmarks",
    "benchmark",
    "migrations",
    "type_check",
    "typing",
}

WEB_MARKERS = {
    "flask",
    "django",
    "fastapi",
    "starlette",
    "uvicorn",
    "gunicorn",
    "express",
    "koa",
    "rails",
    "spring",
}

WEBSITE_MARKERS = {
    "react",
    "next",
    "nextjs",
    "nuxt",
    "vue",
    "angular",
    "sveltekit",
    "gatsby",
    "remix",
}

API_FRAMEWORK_MARKERS = {
    "fastapi",
    "starlette",
    "uvicorn",
    "gunicorn",
    "express",
    "koa",
    "spring",
}

WEBSITE_FRAMEWORK_MARKERS = {
    "django",
    "flask",
    "rails",
}

CLI_MARKERS = {
    "click",
    "typer",
    "argparse",
    "commander",
    "yargs",
    "cobra",
}

DATA_MARKERS = {
    "airflow",
    "pandas",
    "spark",
    "dbt",
    "dask",
    "beam",
}

SDK_MARKERS = {
    "sdk",
    "client",
    "clients",
    "api_client",
    "http_client",
}

FRAMEWORK_MARKERS = {
    "extensions",
    "blueprints",
    "middleware",
    "dispatch",
    "routing",
}

SERVERLESS_MARKERS = {
    "serverless",
    "lambda",
    "functions-framework",
    "azure-functions",
}

DESKTOP_MARKERS = {
    "electron",
    "tauri",
    "pyqt",
    "pyside",
    "wpf",
    "winforms",
}

MOBILE_MARKERS = {
    "react-native",
    "flutter",
    "android",
    "ios",
    "swiftui",
    "jetpack",
}

FIRMWARE_MARKERS = {
    "freertos",
    "stm32",
    "zephyr",
    "arduino",
    "esp-idf",
}

API_DIRECTORY_HINTS = {
    "api",
    "apis",
    "routes",
    "routing",
    "controllers",
    "controller",
    "handlers",
    "handler",
    "serializers",
    "schemas",
    "openapi",
}

WEBSITE_DIRECTORY_HINTS = {
    "templates",
    "static",
    "frontend",
    "web",
    "pages",
    "components",
    "assets",
    "public",
    "ui",
}

FIRMWARE_DIRECTORY_HINTS = {
    "firmware",
    "boards",
    "board",
    "drivers",
    "driver",
    "hal",
    "mcu",
    "embedded",
    "bootloader",
    "rtos",
}

CLOUD_DIRECTORY_HINTS = {
    "cloud",
    "api",
    "apis",
    "services",
    "service",
    "gateway",
    "backend",
    "functions",
    "lambda",
    "lambdas",
}

SERVICE_ROOT_HINTS = {
    "services",
    "apps",
    "gateway",
}

ZONE_REASON_NOISE = "noise_directory"
ZONE_REASON_CRITICAL_DIRECTORY = "critical_directory"
ZONE_REASON_ENTRYPOINT = "entrypoint_file"
ZONE_REASON_WEB_ROUTE = "web_route_path"
ZONE_REASON_WEBSITE_UI = "website_ui_path"
ZONE_REASON_CLI = "cli_surface_path"
ZONE_REASON_PIPELINE = "pipeline_execution_path"
ZONE_REASON_FIRMWARE = "firmware_path"
ZONE_REASON_SERVERLESS = "serverless_function_path"
ZONE_REASON_MOBILE = "mobile_platform_path"
ZONE_REASON_HYBRID_CLOUD = "hybrid_cloud_control_path"
ZONE_REASON_SERVICE_ROOT = "service_root_path"
ZONE_REASON_PRODUCTION = "production_code_path"
ZONE_REASON_SUPPORTING = "supporting_code_path"

ENTRYPOINT_FILES = {
    "main.py",
    "app.py",
    "manage.py",
    "wsgi.py",
    "asgi.py",
    "server.py",
    "cli.py",
}

MANIFEST_MARKER_SETS = (
    WEB_MARKERS
    | CLI_MARKERS
    | DATA_MARKERS
    | SDK_MARKERS
    | SERVERLESS_MARKERS
    | DESKTOP_MARKERS
    | MOBILE_MARKERS
    | FIRMWARE_MARKERS
    | WEBSITE_MARKERS
)


def profile_project(target: Path, files: list[Path]) -> ProjectProfile:
    root = target.resolve()
    relative_files = [path.resolve().relative_to(root) for path in files if path.exists()]
    directory_parts = _directory_parts(root, relative_files)
    filename_markers = {path.name.lower() for path in relative_files}
    primary_languages = _language_counts(files)
    dependency_details = _collect_dependency_markers(root)
    dependency_markers = {item.marker for item in dependency_details}
    entrypoint_markers = sorted(name for name in filename_markers if name in ENTRYPOINT_FILES)
    directory_markers = sorted(
        part
        for part in directory_parts
        if part
        in (
            NOISE_ZONE_NAMES
            | FRAMEWORK_MARKERS
            | {"src", "app", "apps", "api", "services", "workers", "cli", "bin", "ios", "android", "firmware"}
        )
    )

    primary_profile, secondary_profiles = _infer_profiles(
        directory_parts=directory_parts,
        filename_markers=filename_markers,
        dependency_markers=dependency_markers,
        primary_languages=primary_languages,
    )
    execution_models = _infer_execution_models(
        directory_parts=directory_parts,
        dependency_markers=dependency_markers,
        filename_markers=filename_markers,
    )
    surfaces = _infer_surfaces(
        directory_parts=directory_parts,
        dependency_markers=dependency_markers,
        filename_markers=filename_markers,
    )
    web_shape = _infer_web_shape(
        directory_parts=directory_parts,
        dependency_markers=dependency_markers,
        surfaces=surfaces,
        primary_profile=primary_profile,
    )
    service_topology = _infer_service_topology(
        relative_files=relative_files,
        directory_parts=directory_parts,
        execution_models=execution_models,
    )
    hybrid_shape = _infer_hybrid_shape(
        directory_parts=directory_parts,
        dependency_markers=dependency_markers,
        primary_profile=primary_profile,
        secondary_profiles=secondary_profiles,
    )
    primary_objectives, secondary_objectives = _infer_objectives(primary_profile, surfaces, execution_models)
    noise_zones = _noise_zones(directory_parts)
    critical_zones = _critical_zones(
        root=root,
        relative_files=relative_files,
        directory_parts=directory_parts,
        project_type=primary_profile,
    )
    zone_classification = _classify_file_zones(
        relative_files=relative_files,
        dependency_markers=dependency_markers,
        critical_zones=critical_zones,
        noise_zones=noise_zones,
        primary_profile=primary_profile,
        surfaces=surfaces,
        web_shape=web_shape,
        hybrid_shape=hybrid_shape,
    )
    confidence_score, confidence, confidence_factors = _infer_confidence(
        primary_profile=primary_profile,
        dependency_details=dependency_details,
        critical_zones=critical_zones,
        surfaces=surfaces,
        execution_models=execution_models,
        zone_classification=zone_classification,
        secondary_profiles=secondary_profiles,
        web_shape=web_shape,
        service_topology=service_topology,
        hybrid_shape=hybrid_shape,
    )

    explanation = _profile_explanation(
        project_type=primary_profile,
        secondary_profiles=secondary_profiles,
        execution_models=execution_models,
        surfaces=surfaces,
        dependency_markers=dependency_markers,
        noise_zones=noise_zones,
        critical_zones=critical_zones,
        primary_languages=primary_languages,
        confidence=confidence,
        confidence_score=confidence_score,
        web_shape=web_shape,
        service_topology=service_topology,
        hybrid_shape=hybrid_shape,
    )

    return ProjectProfile(
        primary_profile=primary_profile,
        secondary_profiles=secondary_profiles,
        execution_models=execution_models,
        surfaces=surfaces,
        confidence=confidence,
        confidence_score=confidence_score,
        project_type=primary_profile,
        primary_objectives=primary_objectives,
        secondary_objectives=secondary_objectives,
        primary_languages=primary_languages,
        critical_zones=critical_zones,
        noise_zones=noise_zones,
        zone_classification=zone_classification,
        detected_markers=sorted(dependency_markers),
        evidence=ProfileEvidence(
            dependency_markers=sorted(dependency_markers),
            dependency_details=sorted(
                dependency_details,
                key=lambda item: (item.manifest, item.marker, item.source),
            ),
            directory_markers=directory_markers,
            entrypoint_markers=entrypoint_markers,
            language_markers=primary_languages,
            confidence_factors=confidence_factors,
        ),
        explanation=explanation,
        web_shape=web_shape,
        service_topology=service_topology,
        hybrid_shape=hybrid_shape,
    )


def _language_counts(files: list[Path]) -> list[str]:
    counts: Counter[str] = Counter()
    for path in files:
        language = detect_language(path)
        if language != "unsupported":
            counts[language.title()] += 1
    return [name for name, _ in counts.most_common(3)]


def _directory_parts(root: Path, relative_files: list[Path]) -> set[str]:
    parts: set[str] = set()
    for path in root.rglob("*"):
        if path.is_dir():
            parts.add(path.name.lower())
    for path in relative_files:
        for part in path.parts[:-1]:
            parts.add(part.lower())
    return parts


def _collect_dependency_markers(root: Path) -> list[DependencyEvidenceItem]:
    collected: dict[tuple[str, str, str], DependencyEvidenceItem] = {}
    for filename in (
        "pyproject.toml",
        "requirements.txt",
        "package.json",
        "go.mod",
        "Cargo.toml",
        "Gemfile",
        "composer.json",
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        "platformio.ini",
    ):
        path = root / filename
        if not path.exists():
            continue
        for item in _parse_manifest_markers(path):
            collected[(item.manifest, item.marker, item.source)] = item
    return list(collected.values())


def _parse_manifest_markers(path: Path) -> list[DependencyEvidenceItem]:
    if path.name == "pyproject.toml":
        return _parse_pyproject_markers(path)
    if path.name == "package.json":
        return _parse_package_json_markers(path)
    return _parse_manifest_markers_by_content(path)


def _parse_pyproject_markers(path: Path) -> list[DependencyEvidenceItem]:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return _parse_manifest_markers_by_content(path)

    dependencies: list[tuple[str, str]] = []
    project = data.get("project", {})
    dependencies.extend((dep, "project.dependencies") for dep in project.get("dependencies", []))

    optional_dependencies = project.get("optional-dependencies", {})
    for group, group_deps in optional_dependencies.items():
        dependencies.extend((dep, f"project.optional-dependencies.{group}") for dep in group_deps)

    dependency_groups = data.get("dependency-groups", {})
    for group, group_deps in dependency_groups.items():
        dependencies.extend((dep, f"dependency-groups.{group}") for dep in group_deps)

    tool = data.get("tool", {})
    poetry = tool.get("poetry", {})
    dependencies.extend((name, "tool.poetry.dependencies") for name in poetry.get("dependencies", {}).keys())
    dependencies.extend((name, "tool.poetry.group") for name in _flatten_poetry_groups(poetry.get("group", {})))

    return _dependency_items_from_names(path.name, dependencies)


def _flatten_poetry_groups(groups: dict) -> list[str]:
    names: list[str] = []
    for group_data in groups.values():
        dependencies = group_data.get("dependencies", {})
        names.extend(str(name) for name in dependencies.keys())
    return names


def _parse_package_json_markers(path: Path) -> list[DependencyEvidenceItem]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _parse_manifest_markers_by_content(path)

    dependencies: list[tuple[str, str]] = []
    for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        values = data.get(section, {})
        if isinstance(values, dict):
            dependencies.extend((name, section) for name in values.keys())
    return _dependency_items_from_names(path.name, dependencies)


def _parse_manifest_markers_by_content(path: Path) -> list[DependencyEvidenceItem]:
    try:
        content = path.read_text(encoding="utf-8", errors="ignore").lower()
    except OSError:
        return []

    items: list[DependencyEvidenceItem] = []
    for marker in MANIFEST_MARKER_SETS:
        if marker in content:
            items.append(
                DependencyEvidenceItem(
                    marker=marker,
                    manifest=path.name,
                    source="content-match",
                )
            )
    return items


def _dependency_items_from_names(
    manifest_name: str,
    dependencies: list[tuple[str, str]],
) -> list[DependencyEvidenceItem]:
    items: list[DependencyEvidenceItem] = []
    seen: set[tuple[str, str, str]] = set()
    for raw_name, source in dependencies:
        normalized = _normalize_dependency_name(raw_name)
        for marker in _markers_for_dependency_name(normalized):
            key = (manifest_name, marker, source)
            if key in seen:
                continue
            seen.add(key)
            items.append(
                DependencyEvidenceItem(
                    marker=marker,
                    manifest=manifest_name,
                    source=source,
                )
            )
    return items


def _normalize_dependency_name(value: str) -> str:
    name = str(value).strip().lower()
    if ";" in name:
        name = name.split(";", 1)[0].strip()
    for separator in ("[", " ", "=", "<", ">", "!", "~", "^"):
        if separator in name:
            name = name.split(separator, 1)[0].strip()
    return name


def _markers_for_dependency_name(name: str) -> set[str]:
    markers: set[str] = set()
    if not name:
        return markers
    for marker in MANIFEST_MARKER_SETS:
        if name == marker or name.startswith(f"{marker}-") or name.startswith(f"{marker}_"):
            markers.add(marker)
    if name.endswith("-sdk") or name.endswith("_sdk"):
        markers.add("sdk")
    if name.endswith("-client") or name.endswith("_client"):
        markers.add("client")
    return markers


def _infer_profiles(
    directory_parts: set[str],
    filename_markers: set[str],
    dependency_markers: set[str],
    primary_languages: list[str],
) -> tuple[str, list[str]]:
    profiles: list[str] = []
    firmware_weight = len(dependency_markers & FIRMWARE_MARKERS) + len(directory_parts & FIRMWARE_DIRECTORY_HINTS)
    cloud_weight = (
        len(dependency_markers & (WEB_MARKERS | SERVERLESS_MARKERS))
        + len(directory_parts & (API_DIRECTORY_HINTS | CLOUD_DIRECTORY_HINTS))
    )
    website_weight = len(dependency_markers & WEBSITE_MARKERS) + len(directory_parts & WEBSITE_DIRECTORY_HINTS)
    if firmware_weight and cloud_weight and ("firmware" in directory_parts or dependency_markers & FIRMWARE_MARKERS):
        profiles.append("device_firmware")
    if dependency_markers & WEB_MARKERS:
        if "Python" in primary_languages and {"tests", "docs"} <= directory_parts and "src" in directory_parts:
            profiles.append("framework_library")
        else:
            profiles.append("web_backend")
    elif website_weight >= 3:
        profiles.append("web_backend")
    if dependency_markers & CLI_MARKERS or "cli" in directory_parts or "bin" in directory_parts:
        profiles.append("cli_tool")
    if dependency_markers & DATA_MARKERS or {"pipeline", "pipelines", "jobs", "etl"} & directory_parts:
        profiles.append("data_pipeline")
    if dependency_markers & SDK_MARKERS or SDK_MARKERS & directory_parts:
        profiles.append("sdk_library")
    if dependency_markers & DESKTOP_MARKERS:
        profiles.append("desktop_application")
    if dependency_markers & MOBILE_MARKERS or {"ios", "android"} & directory_parts:
        profiles.append("mobile_application")
    if dependency_markers & FIRMWARE_MARKERS or "firmware" in directory_parts or directory_parts & FIRMWARE_DIRECTORY_HINTS:
        profiles.append("device_firmware")
    if dependency_markers & SERVERLESS_MARKERS or {"functions", "lambda", "lambdas"} & directory_parts:
        profiles.append("serverless_application")
    if (
        {"tests", "docs"} <= directory_parts
        and ("src" in directory_parts or "package" in directory_parts or any(name in filename_markers for name in ENTRYPOINT_FILES))
        and "framework_library" not in profiles
    ):
        profiles.append("framework_library")
    if "tests" in directory_parts and len(directory_parts & NOISE_ZONE_NAMES) >= 2 and not profiles:
        profiles.append("test_heavy_repository")
    if not profiles:
        profiles.append("general_application")
    ordered = list(dict.fromkeys(profiles))
    return ordered[0], ordered[1:]


def _infer_objectives(
    project_type: str,
    surfaces: list[str],
    execution_models: list[str],
) -> tuple[list[str], list[str]]:
    mapping = {
        "web_backend": (
            ["request_overhead", "latency", "maintainability"],
            ["startup_time", "serialization_efficiency"],
        ),
        "framework_library": (
            ["api_stability", "extension_stability", "maintainability"],
            ["request_overhead", "startup_time"],
        ),
        "cli_tool": (
            ["startup_time", "user_feedback", "maintainability"],
            ["memory_efficiency", "throughput"],
        ),
        "data_pipeline": (
            ["throughput", "memory_efficiency", "reliability"],
            ["startup_time", "maintainability"],
        ),
        "sdk_library": (
            ["api_stability", "serialization_efficiency", "maintainability"],
            ["request_overhead", "memory_efficiency"],
        ),
        "desktop_application": (
            ["startup_time", "user_feedback", "maintainability"],
            ["memory_efficiency", "api_stability"],
        ),
        "mobile_application": (
            ["startup_time", "battery_efficiency", "network_efficiency"],
            ["maintainability", "memory_efficiency"],
        ),
        "device_firmware": (
            ["reliability", "memory_efficiency", "device_constraints"],
            ["latency", "maintainability"],
        ),
        "serverless_application": (
            ["startup_time", "latency", "reliability"],
            ["request_overhead", "memory_efficiency"],
        ),
        "test_heavy_repository": (
            ["maintainability", "feedback_speed", "test_reliability"],
            ["startup_time"],
        ),
        "general_application": (
            ["maintainability", "efficiency", "readability"],
            ["startup_time", "memory_efficiency"],
        ),
    }
    primary, secondary = mapping[project_type]
    if project_type == "web_backend" and "web_ui" in surfaces:
        primary = ["user_feedback", "request_overhead", "latency"]
        secondary = ["startup_time", "maintainability", "serialization_efficiency"]
    if project_type == "device_firmware" and ("http" in surfaces or "serverless" in execution_models):
        secondary = secondary + ["request_overhead", "reliability"]
    if "http" in surfaces and "request_overhead" not in primary:
        primary = primary + ["request_overhead"]
    if "serverless" in execution_models and "startup_time" not in primary:
        primary = ["startup_time"] + [item for item in primary if item != "startup_time"]
    if "background_jobs" in execution_models and "throughput" not in primary:
        secondary = secondary + ["throughput"]
    return primary, secondary


def _infer_execution_models(
    directory_parts: set[str],
    dependency_markers: set[str],
    filename_markers: set[str],
) -> list[str]:
    models: list[str] = []
    if dependency_markers & WEB_MARKERS or {"routes", "routing", "views", "api"} & directory_parts:
        models.append("request_response")
    if dependency_markers & SERVERLESS_MARKERS or {"functions", "lambda", "lambdas"} & directory_parts:
        models.append("serverless")
    if SERVICE_ROOT_HINTS & directory_parts or "workers" in directory_parts:
        models.append("distributed_services")
    if {"pipeline", "pipelines", "jobs", "workers", "queues"} & directory_parts or dependency_markers & DATA_MARKERS:
        models.append("background_jobs")
    if not models:
        if any(name in filename_markers for name in ENTRYPOINT_FILES):
            models.append("monolith")
        else:
            models.append("library")
    return list(dict.fromkeys(models))


def _infer_surfaces(
    directory_parts: set[str],
    dependency_markers: set[str],
    filename_markers: set[str],
) -> list[str]:
    surfaces: list[str] = []
    if dependency_markers & (WEB_MARKERS | WEBSITE_MARKERS) or {"routes", "routing", "views", "api", "templates"} & directory_parts:
        surfaces.append("http")
    if dependency_markers & CLI_MARKERS or "cli" in directory_parts or "cli.py" in filename_markers:
        surfaces.append("cli")
    if WEBSITE_DIRECTORY_HINTS & directory_parts or dependency_markers & WEBSITE_MARKERS:
        surfaces.append("web_ui")
    if dependency_markers & MOBILE_MARKERS or {"ios", "android"} & directory_parts:
        surfaces.append("mobile")
    if dependency_markers & DESKTOP_MARKERS:
        surfaces.append("desktop")
    if dependency_markers & SDK_MARKERS:
        surfaces.append("sdk")
    if dependency_markers & FIRMWARE_MARKERS or "firmware" in directory_parts:
        surfaces.append("device")
    return list(dict.fromkeys(surfaces))


def _infer_web_shape(
    directory_parts: set[str],
    dependency_markers: set[str],
    surfaces: list[str],
    primary_profile: str,
) -> str | None:
    if primary_profile not in {"web_backend", "framework_library"} and "http" not in surfaces and "web_ui" not in surfaces:
        return None

    api_score = 0
    website_score = 0
    if dependency_markers & API_FRAMEWORK_MARKERS:
        api_score += 3
    if dependency_markers & WEBSITE_FRAMEWORK_MARKERS:
        website_score += 2
    if dependency_markers & WEBSITE_MARKERS:
        website_score += 4
    if dependency_markers & WEB_MARKERS:
        api_score += 2
    if directory_parts & API_DIRECTORY_HINTS:
        api_score += 2
    if "http" in surfaces:
        api_score += 1
    if directory_parts & WEBSITE_DIRECTORY_HINTS:
        website_score += 3
    if "web_ui" in surfaces:
        website_score += 2
    if {"templates", "pages", "components"} & directory_parts:
        website_score += 1
    if {"api", "routes", "controllers", "handlers"} & directory_parts:
        api_score += 1

    if api_score >= 4 and website_score >= 5:
        return "mixed_web_surface"
    if website_score >= api_score + 2 and website_score >= 5:
        return "website_web_app"
    if api_score >= website_score and api_score >= 4:
        return "api_service"
    if primary_profile == "web_backend":
        return "api_service"
    return None


def _infer_service_topology(
    relative_files: list[Path],
    directory_parts: set[str],
    execution_models: list[str],
) -> str | None:
    if "distributed_services" not in execution_models and not (SERVICE_ROOT_HINTS & directory_parts):
        return None

    service_units: dict[str, set[str]] = {}
    root_entrypoints = 0
    for path in relative_files:
        parts = [part.lower() for part in path.parts]
        if len(parts) >= 2 and parts[0] in {"gateway"} and parts[-1] in ENTRYPOINT_FILES | {"server.js", "index.js", "main.ts", "server.ts", "app.js"}:
            root_entrypoints += 1
        if len(parts) < 3:
            continue
        if parts[0] not in {"services", "apps"}:
            continue
        service_units.setdefault(f"{parts[0]}/{parts[1]}", set()).add(parts[-1])

    entrypoint_like = 0
    for filenames in service_units.values():
        if filenames & ENTRYPOINT_FILES or {"server.js", "index.js", "main.ts", "server.ts", "app.js"} & filenames:
            entrypoint_like += 1

    if len(service_units) >= 2 and entrypoint_like >= 2:
        return "microservices"
    if len(service_units) >= 1 or root_entrypoints >= 1 or "distributed_services" in execution_models or SERVICE_ROOT_HINTS & directory_parts:
        return "distributed_monolith"
    return None


def _infer_hybrid_shape(
    directory_parts: set[str],
    dependency_markers: set[str],
    primary_profile: str,
    secondary_profiles: list[str],
) -> str | None:
    firmware_present = bool(
        (dependency_markers & FIRMWARE_MARKERS)
        or (directory_parts & FIRMWARE_DIRECTORY_HINTS)
        or primary_profile == "device_firmware"
        or "device_firmware" in secondary_profiles
    )
    serverless_present = bool(
        (dependency_markers & SERVERLESS_MARKERS)
        or {"functions", "lambda", "lambdas"} & directory_parts
        or primary_profile == "serverless_application"
        or "serverless_application" in secondary_profiles
    )
    cloud_present = bool(
        (dependency_markers & (WEB_MARKERS | SERVERLESS_MARKERS))
        or (directory_parts & CLOUD_DIRECTORY_HINTS)
        or primary_profile in {"web_backend", "serverless_application"}
        or {"web_backend", "serverless_application"} & set(secondary_profiles)
    )
    if firmware_present and cloud_present:
        if serverless_present:
            return "device_firmware_serverless"
        return "device_firmware_cloud"
    return None


def _infer_confidence(
    primary_profile: str,
    dependency_details: list[DependencyEvidenceItem],
    critical_zones: list[str],
    surfaces: list[str],
    execution_models: list[str],
    zone_classification: list[FileZoneClassification],
    secondary_profiles: list[str],
    web_shape: str | None,
    service_topology: str | None,
    hybrid_shape: str | None,
) -> tuple[int, str, list[ConfidenceFactor]]:
    structured_sources = {item.manifest for item in dependency_details if item.source != "content-match"}
    critical_file_count = sum(1 for item in zone_classification if item.zone == "critical")
    dependency_source_count = len({item.source for item in dependency_details if item.source != "content-match"})
    shape_alignment = _shape_alignment_score(
        primary_profile=primary_profile,
        surfaces=surfaces,
        execution_models=execution_models,
        web_shape=web_shape,
        service_topology=service_topology,
        hybrid_shape=hybrid_shape,
    )
    factors = [
        ConfidenceFactor(
            name="structured_dependency_evidence",
            weight=4,
            matched=bool(structured_sources),
            evidence="Structured manifest parsing found dependency markers.",
        ),
        ConfidenceFactor(
            name="structured_dependency_depth",
            weight=2,
            matched=dependency_source_count >= 2,
            evidence="Structured dependency evidence came from multiple sections or manifests.",
        ),
        ConfidenceFactor(
            name="multi_manifest_support",
            weight=2,
            matched=len(structured_sources) >= 2,
            evidence="Multiple structured manifests agree on repository intent.",
        ),
        ConfidenceFactor(
            name="fallback_dependency_evidence",
            weight=2,
            matched=bool(dependency_details),
            evidence="Manifest content produced recognizable dependency markers.",
        ),
        ConfidenceFactor(
            name="critical_zone_evidence",
            weight=2,
            matched=bool(critical_zones),
            evidence="Critical directories were inferred from repository layout.",
        ),
        ConfidenceFactor(
            name="surface_evidence",
            weight=2,
            matched=bool(surfaces),
            evidence="User-facing or service surfaces were identified.",
        ),
        ConfidenceFactor(
            name="execution_model_evidence",
            weight=1,
            matched=bool(execution_models),
            evidence="Execution model hints were identified.",
        ),
        ConfidenceFactor(
            name="file_zone_coverage",
            weight=2,
            matched=critical_file_count >= 1,
            evidence="Per-file zone classification identified critical paths.",
        ),
        ConfidenceFactor(
            name="critical_zone_density",
            weight=2,
            matched=critical_file_count >= 2,
            evidence="Multiple files land in inferred critical zones.",
        ),
        ConfidenceFactor(
            name="specific_profile_shape",
            weight=1,
            matched=primary_profile != "general_application" or bool(secondary_profiles),
            evidence="The repository shape is more specific than the generic fallback.",
        ),
        ConfidenceFactor(
            name="shape_signal_alignment",
            weight=3,
            matched=shape_alignment >= 2,
            evidence="Independent dimensions agree on the refined project shape.",
        ),
        ConfidenceFactor(
            name="web_shape_specificity",
            weight=2,
            matched=web_shape is not None,
            evidence="Web repositories were narrowed to API, website, or mixed web shape.",
        ),
        ConfidenceFactor(
            name="service_topology_specificity",
            weight=2,
            matched=service_topology is not None,
            evidence="Distributed repositories were narrowed to a topology shape.",
        ),
        ConfidenceFactor(
            name="hybrid_repo_specificity",
            weight=3,
            matched=hybrid_shape is not None,
            evidence="Mixed firmware and cloud evidence was identified.",
        ),
    ]
    score = sum(factor.weight for factor in factors if factor.matched)
    if score >= 12:
        label = "high"
    elif score >= 6:
        label = "moderate"
    else:
        label = "low"
    return score, label, factors


def _shape_alignment_score(
    primary_profile: str,
    surfaces: list[str],
    execution_models: list[str],
    web_shape: str | None,
    service_topology: str | None,
    hybrid_shape: str | None,
) -> int:
    score = 0
    if web_shape == "api_service" and "http" in surfaces:
        score += 1
    if web_shape == "website_web_app" and "web_ui" in surfaces:
        score += 1
    if web_shape == "mixed_web_surface" and {"http", "web_ui"} <= set(surfaces):
        score += 1
    if service_topology is not None and "distributed_services" in execution_models:
        score += 1
    if hybrid_shape == "device_firmware_serverless" and "serverless" in execution_models:
        score += 1
    if hybrid_shape is not None and primary_profile == "device_firmware":
        score += 1
    return score


def _noise_zones(directory_parts: set[str]) -> list[str]:
    return sorted(zone for zone in directory_parts if zone in NOISE_ZONE_NAMES)


def _critical_zones(
    root: Path,
    relative_files: list[Path],
    directory_parts: set[str],
    project_type: str,
) -> list[str]:
    critical: list[str] = []
    preferred_dirs = ["src", "app", "apps", "flask", "core", "lib", "package", "services", "gateway", "firmware"]
    for name in preferred_dirs:
        if name in directory_parts:
            critical.append(name)
    if project_type in {"web_backend", "framework_library"}:
        for name in ("views", "routes", "routing", "dispatch", "templates", "blueprints"):
            if name in directory_parts:
                critical.append(name)
    if project_type == "cli_tool":
        for name in ("cli", "commands", "bin"):
            if name in directory_parts:
                critical.append(name)
    if project_type == "data_pipeline":
        for name in ("pipeline", "pipelines", "jobs", "etl"):
            if name in directory_parts:
                critical.append(name)
    if project_type == "device_firmware":
        for name in ("boards", "drivers", "hal", "mcu", "bootloader"):
            if name in directory_parts:
                critical.append(name)

    if not critical:
        top_level_dirs = []
        for path in relative_files:
            if len(path.parts) > 1:
                candidate = path.parts[0]
                if candidate.lower() not in NOISE_ZONE_NAMES:
                    top_level_dirs.append(candidate)
        critical.extend(sorted(dict.fromkeys(top_level_dirs))[:3])

    return sorted(dict.fromkeys(critical))


def _profile_explanation(
    project_type: str,
    secondary_profiles: list[str],
    execution_models: list[str],
    surfaces: list[str],
    dependency_markers: set[str],
    noise_zones: list[str],
    critical_zones: list[str],
    primary_languages: list[str],
    confidence: str,
    confidence_score: int,
    web_shape: str | None,
    service_topology: str | None,
    hybrid_shape: str | None,
) -> str:
    marker_note = ", ".join(sorted(dependency_markers)) if dependency_markers else "no strong framework markers"
    noise_note = ", ".join(noise_zones) if noise_zones else "no obvious noise zones"
    critical_note = ", ".join(critical_zones) if critical_zones else "no dominant critical zones inferred yet"
    languages_note = ", ".join(primary_languages) if primary_languages else "unknown language mix"
    secondary_note = ", ".join(secondary_profiles) if secondary_profiles else "none"
    execution_note = ", ".join(execution_models) if execution_models else "not inferred"
    surfaces_note = ", ".join(surfaces) if surfaces else "not inferred"
    web_shape_note = web_shape.replace("_", " ") if web_shape else "not refined"
    topology_note = service_topology.replace("_", " ") if service_topology else "not refined"
    hybrid_note = hybrid_shape.replace("_", " ") if hybrid_shape else "not inferred"
    return (
        f"Stage 1 profile classifies this repository as {project_type.replace('_', ' ')} with confidence {confidence} "
        f"(score {confidence_score}). "
        f"Primary language signals: {languages_note}. "
        f"Secondary profile signals: {secondary_note}. "
        f"Execution models: {execution_note}. "
        f"Surfaces: {surfaces_note}. "
        f"Web shape: {web_shape_note}. "
        f"Service topology: {topology_note}. "
        f"Hybrid shape: {hybrid_note}. "
        f"Detected markers: {marker_note}. "
        f"Likely noise zones: {noise_note}. "
        f"Likely critical zones: {critical_note}."
    )


def _classify_file_zones(
    relative_files: list[Path],
    dependency_markers: set[str],
    critical_zones: list[str],
    noise_zones: list[str],
    primary_profile: str,
    surfaces: list[str],
    web_shape: str | None,
    hybrid_shape: str | None,
) -> list[FileZoneClassification]:
    classifications: list[FileZoneClassification] = []
    critical_set = {zone.lower() for zone in critical_zones}
    noise_set = {zone.lower() for zone in noise_zones}
    for path in sorted(relative_files, key=lambda item: str(item).lower()):
        parts = [part.lower() for part in path.parts[:-1]]
        filename = path.name.lower()
        reasons: list[str] = []
        zone = "supporting"

        if any(part in noise_set for part in parts):
            zone = "noise"
            reasons.append(ZONE_REASON_NOISE)
        elif any(part in critical_set for part in parts):
            zone = "critical"
            reasons.append(ZONE_REASON_CRITICAL_DIRECTORY)
        elif filename in ENTRYPOINT_FILES:
            zone = "critical"
            reasons.append(ZONE_REASON_ENTRYPOINT)
        elif primary_profile in {"web_backend", "framework_library"} and {"api", "routes", "views", "templates"} & set(parts):
            zone = "critical"
            reasons.append(ZONE_REASON_WEB_ROUTE)
        elif web_shape == "website_web_app" and WEBSITE_DIRECTORY_HINTS & set(parts):
            zone = "critical"
            reasons.append(ZONE_REASON_WEBSITE_UI)
        elif "cli" in surfaces and {"cli", "commands", "bin"} & set(parts):
            zone = "critical"
            reasons.append(ZONE_REASON_CLI)
        elif primary_profile == "data_pipeline" and {"pipeline", "pipelines", "jobs", "etl", "workers"} & set(parts):
            zone = "critical"
            reasons.append(ZONE_REASON_PIPELINE)
        elif primary_profile == "device_firmware" and FIRMWARE_DIRECTORY_HINTS & set(parts):
            zone = "critical"
            reasons.append(ZONE_REASON_FIRMWARE)
        elif SERVICE_ROOT_HINTS & set(parts):
            zone = "supporting"
            reasons.append(ZONE_REASON_SERVICE_ROOT)
        elif {"services", "core", "lib", "app", "src"} & set(parts):
            zone = "supporting"
            reasons.append(ZONE_REASON_PRODUCTION)
        else:
            zone = "supporting"
            reasons.append(ZONE_REASON_SUPPORTING)

        if primary_profile in {"web_backend", "framework_library"} and {"api", "routes", "views", "templates"} & set(parts):
            reasons.append(ZONE_REASON_WEB_ROUTE)
        if web_shape == "website_web_app" and WEBSITE_DIRECTORY_HINTS & set(parts):
            reasons.append(ZONE_REASON_WEBSITE_UI)
        if "cli" in surfaces and {"cli", "commands", "bin"} & set(parts):
            reasons.append(ZONE_REASON_CLI)
        if primary_profile == "data_pipeline" and {"pipeline", "pipelines", "jobs", "etl", "workers"} & set(parts):
            reasons.append(ZONE_REASON_PIPELINE)
        if primary_profile == "device_firmware" and FIRMWARE_DIRECTORY_HINTS & set(parts):
            reasons.append(ZONE_REASON_FIRMWARE)
        if dependency_markers & SERVERLESS_MARKERS and {"functions", "lambda", "lambdas"} & set(parts):
            zone = "critical"
            reasons.append(ZONE_REASON_SERVERLESS)
        if dependency_markers & MOBILE_MARKERS and {"ios", "android"} & set(parts):
            zone = "critical"
            reasons.append(ZONE_REASON_MOBILE)
        if hybrid_shape is not None and CLOUD_DIRECTORY_HINTS & set(parts):
            zone = "critical"
            reasons.append(ZONE_REASON_HYBRID_CLOUD)

        classifications.append(
            FileZoneClassification(
                file=str(path),
                zone=zone,
                reasons=sorted(dict.fromkeys(reasons)),
            )
        )
    return classifications
