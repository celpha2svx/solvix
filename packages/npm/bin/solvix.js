#!/usr/bin/env node

const { spawnSync } = require("child_process");

const PYTHON_ERROR =
  "Solvix requires Python 3.10 or higher. Install Python from python.org then run pip install solvix";
const PACKAGE_ERROR =
  "Solvix Python package not found. Run pip install solvix first then retry";

const PYTHON_CANDIDATES = [
  { command: "py", args: ["-3"] },
  { command: "python3", args: [] },
  { command: "python", args: [] },
];

function run(command, args) {
  return spawnSync(command, args, {
    encoding: "utf8",
    windowsHide: true,
  });
}

function detectPython() {
  const versionCheck =
    "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)";

  for (const candidate of PYTHON_CANDIDATES) {
    const result = run(candidate.command, [...candidate.args, "-c", versionCheck]);
    if (!result.error && result.status === 0) {
      return candidate;
    }
  }

  return null;
}

function hasSolvixPackage(candidate) {
  const check =
    "import importlib.metadata, sys; sys.exit(0 if importlib.metadata.version('solvix') else 1)";
  const result = run(candidate.command, [...candidate.args, "-c", check]);
  return !result.error && result.status === 0;
}

function launchSolvix(candidate) {
  const result = spawnSync(
    candidate.command,
    [...candidate.args, "-m", "cli.main", ...process.argv.slice(2)],
    {
      stdio: "inherit",
      windowsHide: true,
    }
  );

  if (result.error) {
    console.error(result.error.message);
    process.exit(1);
  }

  process.exit(result.status === null ? 1 : result.status);
}

const python = detectPython();
if (!python) {
  console.error(PYTHON_ERROR);
  process.exit(1);
}

if (!hasSolvixPackage(python)) {
  console.error(PACKAGE_ERROR);
  process.exit(1);
}

launchSolvix(python);
