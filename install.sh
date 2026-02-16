#!/usr/bin/env bash
set -euo pipefail

KERN_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/kern"
BIN_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"
REPO="0xjgv/kern"
VENV_DIR="$KERN_DIR/.venv"

# Colors (disabled if not a terminal)
if [[ -t 1 ]]; then
  RED='\033[0;31m' GREEN='\033[0;32m' YELLOW='\033[0;33m' NC='\033[0m'
else
  RED='' GREEN='' YELLOW='' NC=''
fi

info() { printf '%b\n' "${GREEN}==>${NC} $1"; }
warn() { printf '%b\n' "${YELLOW}Warning:${NC} $1"; }
error() { printf '%b\n' "${RED}Error:${NC} $1" >&2; exit 1; }

compute_sha256() {
  local file="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$file" | cut -d' ' -f1
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$file" | cut -d' ' -f1
  else
    echo ""
  fi
}

verify_checksum() {
  local file="$1" expected="$2"
  local actual
  actual=$(compute_sha256 "$file")
  if [[ -z "$actual" ]]; then
    warn "No checksum tool available, skipping verification"
    return 0
  fi
  if [[ "$actual" != "$expected" ]]; then
    error "Checksum mismatch! Expected: $expected, Got: $actual"
  fi
  info "Checksum verified"
}

download() {
  local url="$1" output="$2"
  curl --fail --silent --show-error --location \
    --proto '=https' --tlsv1.2 \
    --retry 3 --retry-delay 2 \
    -o "$output" "$url"
}

info "Checking dependencies..."
command -v git >/dev/null 2>&1 || error "Required: git"
command -v curl >/dev/null 2>&1 || error "Required: curl"
command -v python3 >/dev/null 2>&1 || error "Required: python3"

if ! command -v claude >/dev/null 2>&1; then
  warn "claude CLI not found. Install from: https://docs.anthropic.com/en/docs/claude-code"
  warn "kern requires claude CLI to run. Continuing installation anyway..."
fi

info "Installing to $KERN_DIR..."
mkdir -p "$KERN_DIR" "$BIN_DIR"

TEMP_DIR=$(mktemp -d) || error "Failed to create temp directory"
chmod 700 "$TEMP_DIR"
trap 'rm -rf "$TEMP_DIR"' EXIT INT TERM

DOWNLOAD_URL="https://github.com/$REPO/releases/latest/download/kern.tar.gz"
ARCHIVE="$TEMP_DIR/kern.tar.gz"

if download "$DOWNLOAD_URL" "$ARCHIVE" 2>/dev/null; then
  if download "${DOWNLOAD_URL}.sha256" "$TEMP_DIR/kern.tar.gz.sha256" 2>/dev/null; then
    EXPECTED=$(cut -d' ' -f1 "$TEMP_DIR/kern.tar.gz.sha256")
    verify_checksum "$ARCHIVE" "$EXPECTED"
  else
    error "No checksum file available. Verification is required for security."
  fi
else
  warn "No release found, installing from main branch (unverified)"
  if ! download "https://github.com/$REPO/archive/refs/heads/main.tar.gz" "$TEMP_DIR/main.tar.gz"; then
    error "Failed to download from main branch"
  fi
  ARCHIVE="$TEMP_DIR/main.tar.gz"
fi

rm -rf "$KERN_DIR/src" "$KERN_DIR/prompts"
rm -f "$KERN_DIR"/pyproject.toml "$KERN_DIR"/README.md "$KERN_DIR"/CLAUDE.md "$KERN_DIR"/kern.sh "$KERN_DIR"/install.sh "$KERN_DIR"/agents.json

if [[ "$ARCHIVE" == *"/main.tar.gz" ]]; then
  tar xzf "$ARCHIVE" -C "$TEMP_DIR" || error "Failed to extract archive"
  SRC_DIR="$TEMP_DIR/kern-main"
  cp -R "$SRC_DIR/src" "$KERN_DIR/"
  cp -R "$SRC_DIR/prompts" "$KERN_DIR/"
  cp "$SRC_DIR/pyproject.toml" "$KERN_DIR/"
  cp "$SRC_DIR/README.md" "$KERN_DIR/"
  cp "$SRC_DIR/CLAUDE.md" "$KERN_DIR/"
  cp "$SRC_DIR/kern.sh" "$KERN_DIR/"
  cp "$SRC_DIR/install.sh" "$KERN_DIR/"
  cp "$SRC_DIR/agents.json" "$KERN_DIR/"
else
  tar xzf "$ARCHIVE" -C "$KERN_DIR" || error "Failed to extract archive"
fi

chmod +x "$KERN_DIR/kern.sh"

info "Creating managed virtualenv at $VENV_DIR..."
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip >/dev/null
"$VENV_DIR/bin/pip" install "$KERN_DIR" >/dev/null

ln -sf "$VENV_DIR/bin/kern" "$BIN_DIR/kern"
info "Installed kern to $BIN_DIR/kern"

if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
  warn "$BIN_DIR is not in your PATH"
  echo ""
  echo "Add this to your shell profile (~/.bashrc, ~/.zshrc, etc.):"
  echo ""
  echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
  echo ""
fi

echo ""
"$BIN_DIR/kern" --version
info "Run 'kern --help' to get started"
