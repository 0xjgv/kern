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

# Dependency checks
info "Checking dependencies..."
command -v git >/dev/null 2>&1 || error "Required: git"

if ! command -v claude >/dev/null 2>&1; then
  warn "claude CLI not found. Install from: https://docs.anthropic.com/en/docs/claude-code"
  warn "kern requires claude CLI to run. Continuing installation anyway..."
fi

# Create directories
info "Installing to $KERN_DIR..."
mkdir -p "$KERN_DIR" "$BIN_DIR"

# Download latest release
DOWNLOAD_URL="https://github.com/$REPO/releases/latest/download/kern.tar.gz"
if ! curl -fsSL "$DOWNLOAD_URL" | tar xz -C "$KERN_DIR" 2>/dev/null; then
  # Fallback: clone from main branch if no release exists
  info "No release found, installing from main branch..."
  TEMP_DIR=$(mktemp -d)
  trap "rm -rf '$TEMP_DIR'" EXIT

  curl -fsSL "https://github.com/$REPO/archive/refs/heads/main.tar.gz" | tar xz -C "$TEMP_DIR"

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
