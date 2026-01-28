#!/bin/bash
set -e

VERSION="${1:-}"

if [[ -z "$VERSION" ]]; then
  echo "Usage: ./scripts/release.sh <version>"
  echo "Example: ./scripts/release.sh 0.1.5"
  exit 1
fi

if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Error: Version must be in format X.Y.Z"
  exit 1
fi

if git ls-remote --tags origin | grep -q "refs/tags/v${VERSION}$"; then
  echo "Error: Tag v${VERSION} already exists"
  exit 1
fi

echo "Releasing v${VERSION}..."

# Push any pending commits
git push origin main

# Trigger release workflow
gh workflow run release.yml -f version="$VERSION"

echo "Workflow triggered. View at: https://github.com/$(gh repo view --json nameWithOwner -q .nameWithOwner)/actions"
