#!/usr/bin/env sh
set -eu

REPO="celpha2svx/solvix"
VERSION="${SOLVIX_VERSION:-latest}"
INSTALL_DIR="${SOLVIX_INSTALL_DIR:-$HOME/.local/bin}"

resolve_version() {
  if [ "$VERSION" != "latest" ]; then
    printf '%s' "$VERSION"
    return
  fi

  curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" \
    | sed -n 's/.*"tag_name":[[:space:]]*"\(v[^"]*\)".*/\1/p' \
    | head -n 1
}

detect_asset() {
  os="$(uname -s)"
  arch="$(uname -m)"

  case "$os" in
    Linux) platform="linux" ;;
    Darwin) platform="macos" ;;
    *)
      echo "Solvix install script supports Linux and macOS only." >&2
      exit 1
      ;;
  esac

  case "$arch" in
    x86_64|amd64) cpu="x64" ;;
    arm64|aarch64) cpu="arm64" ;;
    *)
      echo "Unsupported architecture: $arch" >&2
      exit 1
      ;;
  esac

  printf 'solvix-%s-%s' "$platform" "$cpu"
}

verify_sha256() {
  file="$1"
  expected="$2"

  if command -v sha256sum >/dev/null 2>&1; then
    actual="$(sha256sum "$file" | awk '{print $1}')"
  elif command -v shasum >/dev/null 2>&1; then
    actual="$(shasum -a 256 "$file" | awk '{print $1}')"
  elif command -v openssl >/dev/null 2>&1; then
    actual="$(openssl dgst -sha256 "$file" | awk '{print $NF}')"
  else
    echo "No SHA-256 tool found. Install sha256sum, shasum, or openssl." >&2
    exit 1
  fi

  if [ "$actual" != "$expected" ]; then
    echo "Checksum verification failed for $file" >&2
    exit 1
  fi
}

TAG="$(resolve_version)"
if [ -z "$TAG" ]; then
  echo "Could not resolve the latest Solvix release tag." >&2
  exit 1
fi

ASSET="$(detect_asset)"
BASE_URL="https://github.com/$REPO/releases/download/$TAG"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT INT TERM

BINARY_PATH="$TMP_DIR/$ASSET"
CHECKSUM_PATH="$TMP_DIR/$ASSET.sha256"

curl -fsSL "$BASE_URL/$ASSET" -o "$BINARY_PATH"
curl -fsSL "$BASE_URL/$ASSET.sha256" -o "$CHECKSUM_PATH"

EXPECTED_SHA="$(awk '{print $1}' "$CHECKSUM_PATH")"
verify_sha256 "$BINARY_PATH" "$EXPECTED_SHA"

mkdir -p "$INSTALL_DIR"
cp "$BINARY_PATH" "$INSTALL_DIR/solvix"
chmod +x "$INSTALL_DIR/solvix"

echo "Solvix installed to $INSTALL_DIR/solvix"
case ":$PATH:" in
  *":$INSTALL_DIR:"*) ;;
  *)
    echo "Add $INSTALL_DIR to PATH if it is not already available in your shell."
    ;;
esac
