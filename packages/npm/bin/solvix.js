#!/usr/bin/env node

const fs = require("fs");
const os = require("os");
const path = require("path");
const https = require("https");
const { spawnSync } = require("child_process");

const PACKAGE = require("../package.json");
const VERSION = PACKAGE.version;
const REPO = "celpha2svx/solvix";
const RELEASE_TAG = `v${VERSION}`;
const CACHE_ROOT = getCacheRoot();
const CACHE_DIR = path.join(CACHE_ROOT, "solvix", VERSION);
const EXECUTABLE_NAME = resolveExecutableName();
const EXECUTABLE_PATH = path.join(CACHE_DIR, EXECUTABLE_NAME);

function getCacheRoot() {
  if (process.platform === "win32") {
    return process.env.LOCALAPPDATA || path.join(os.homedir(), "AppData", "Local");
  }
  if (process.platform === "darwin") {
    return path.join(os.homedir(), "Library", "Caches");
  }
  return process.env.XDG_CACHE_HOME || path.join(os.homedir(), ".cache");
}

function resolveExecutableName() {
  const platform = process.platform;
  const arch = process.arch;

  if (platform === "win32" && arch === "x64") return "solvix-windows-x64.exe";
  if (platform === "win32" && arch === "arm64") return "solvix-windows-arm64.exe";
  if (platform === "linux" && arch === "x64") return "solvix-linux-x64";
  if (platform === "linux" && arch === "arm64") return "solvix-linux-arm64";
  if (platform === "darwin" && arch === "x64") return "solvix-macos-x64";
  if (platform === "darwin" && arch === "arm64") return "solvix-macos-arm64";

  console.error(
    `Solvix does not yet provide a prebuilt binary for platform ${platform}/${arch}.`
  );
  process.exit(1);
}

function releaseUrl() {
  return `https://github.com/${REPO}/releases/download/${RELEASE_TAG}/${EXECUTABLE_NAME}`;
}

function ensureBinary() {
  if (fs.existsSync(EXECUTABLE_PATH)) {
    return;
  }

  fs.mkdirSync(CACHE_DIR, { recursive: true });
  downloadBinary(releaseUrl(), EXECUTABLE_PATH);
  if (process.platform !== "win32") {
    fs.chmodSync(EXECUTABLE_PATH, 0o755);
  }
}

function downloadBinary(url, destination) {
  const file = fs.createWriteStream(destination);

  const request = (target) => {
    https
      .get(target, (response) => {
        if (
          response.statusCode &&
          response.statusCode >= 300 &&
          response.statusCode < 400 &&
          response.headers.location
        ) {
          file.close();
          fs.unlinkSync(destination);
          request(response.headers.location);
          return;
        }

        if (response.statusCode !== 200) {
          file.close();
          fs.unlinkSync(destination);
          console.error(
            `Solvix binary download failed from ${target} (status ${response.statusCode}). ` +
              "Verify that the GitHub release exists and includes the platform binary."
          );
          process.exit(1);
        }

        response.pipe(file);
        file.on("finish", () => file.close());
      })
      .on("error", (error) => {
        file.close();
        if (fs.existsSync(destination)) {
          fs.unlinkSync(destination);
        }
        console.error(
          `Solvix binary download failed: ${error.message}. ` +
            "Check your network connection or install from GitHub Releases manually."
        );
        process.exit(1);
      });
  };

  request(url);
}

function launch() {
  ensureBinary();

  const result = spawnSync(EXECUTABLE_PATH, process.argv.slice(2), {
    stdio: "inherit",
    windowsHide: true,
  });

  if (result.error) {
    console.error(result.error.message);
    process.exit(1);
  }

  process.exit(result.status === null ? 1 : result.status);
}

launch();
