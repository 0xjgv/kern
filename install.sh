#!/usr/bin/env bash
set -euo pipefail

KERN_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/kern"
BIN_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"
REPO="0xjgv/kern"

# Colors (disabled if not a terminal)
if [[ -t 1 ]]; then
  RED='\033[0;31m' GREEN='\033[0;32m' YELLOW='\033[0;33m' NC='\033[0m'
else
  RED='' GREEN='' YELLOW='' NC=''
fi

info() { printf '%b\n' "${GREEN}==>${NC} $1"; }
warn() { printf '%b\n' "${YELLOW}Warning:${NC} $1"; }
error() { printf '%b\n' "${RED}Error:${NC} $1" >&2; exit 1; }

# Platform-independent checksum computation
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

# Verify checksum matches expected value
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

# Secure download with TLS 1.2+ and retries
download() {
  local url="$1" output="$2"
  curl --fail --silent --show-error --location \
    --proto '=https' --tlsv1.2 \
    --retry 3 --retry-delay 2 \
    -o "$output" "$url"
}

# Dependency checks
info "Checking dependencies..."
command -v git >/dev/null 2>&1 || error "Required: git"
command -v curl >/dev/null 2>&1 || error "Required: curl"

if ! command -v claude >/dev/null 2>&1; then
  warn "claude CLI not found. Install from: https://docs.anthropic.com/en/docs/claude-code"
  warn "kern requires claude CLI to run. Continuing installation anyway..."
fi

# Create directories
info "Installing to $KERN_DIR..."
mkdir -p "$KERN_DIR" "$BIN_DIR"

# Clean old prompts to avoid stale files mixing with new ones
rm -rf "$KERN_DIR/prompts"

# Create secure temp directory
TEMP_DIR=$(mktemp -d) || error "Failed to create temp directory"
chmod 700 "$TEMP_DIR"
trap 'rm -rf "$TEMP_DIR"' EXIT INT TERM

# Download latest release
DOWNLOAD_URL="https://github.com/$REPO/releases/latest/download/kern.tar.gz"

if download "$DOWNLOAD_URL" "$TEMP_DIR/kern.tar.gz" 2>/dev/null; then
  # Try to download and verify checksum
  if download "${DOWNLOAD_URL}.sha256" "$TEMP_DIR/kern.tar.gz.sha256" 2>/dev/null; then
    EXPECTED=$(cut -d' ' -f1 "$TEMP_DIR/kern.tar.gz.sha256")
    verify_checksum "$TEMP_DIR/kern.tar.gz" "$EXPECTED"
  else
    warn "No checksum file available, skipping verification"
  fi

  tar xzf "$TEMP_DIR/kern.tar.gz" -C "$KERN_DIR" || error "Failed to extract archive"
else
  # Fallback: clone from main branch if no release exists
  warn "No release found, installing from main branch (unverified)"

  if ! download "https://github.com/$REPO/archive/refs/heads/main.tar.gz" "$TEMP_DIR/main.tar.gz"; then
    error "Failed to download from main branch"
  fi

  tar xzf "$TEMP_DIR/main.tar.gz" -C "$TEMP_DIR" || error "Failed to extract archive"

  cp "$TEMP_DIR"/kern-main/kern.sh "$KERN_DIR/"
  cp -r "$TEMP_DIR"/kern-main/prompts "$KERN_DIR/"
fi

# Create symlink
ln -sf "$KERN_DIR/kern.sh" "$BIN_DIR/kern"
chmod +x "$KERN_DIR/kern.sh"

info "Installed kern to $BIN_DIR/kern"

# Check if BIN_DIR is in PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
  warn "$BIN_DIR is not in your PATH"
  echo ""
  echo "Add this to your shell profile (~/.bashrc, ~/.zshrc, etc.):"
  echo ""
  echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
  echo ""
fi

# Show version
echo ""
"$BIN_DIR/kern" --version
info "Run 'kern --help' to get started"
