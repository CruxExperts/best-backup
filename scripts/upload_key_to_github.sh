#!/bin/bash
# Upload bbackup public key to GitHub gist
# Usage: ./upload_key_to_github.sh [key_file] [gist_description]

set -e

KEY_FILE="${1:-$HOME/.config/bbackup/backup_public.pem}"
GIST_DESCRIPTION="${2:-bbackup encryption public key}"

if [ ! -f "$KEY_FILE" ]; then
    echo "Error: Key file not found: $KEY_FILE"
    echo "Usage: $0 [key_file] [gist_description]"
    exit 1
fi

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "Error: GitHub CLI (gh) is not installed"
    echo "Install it from: https://cli.github.com/"
    exit 1
fi

# Check if logged in
if ! gh auth status &> /dev/null; then
    echo "Error: Not logged into GitHub"
    echo "Run: gh auth login"
    exit 1
fi

# Get username
USERNAME=$(gh api user --jq .login)

echo "Uploading public key to GitHub..."
echo "  Key file: $KEY_FILE"
echo "  Username: $USERNAME"
echo "  Gist description: $GIST_DESCRIPTION"
echo ""

TEMP_DIR=$(mktemp -d)
cleanup() {
    rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

STAGED_KEY="$TEMP_DIR/backup_public.pem"
cp "$KEY_FILE" "$STAGED_KEY"

# Create gist with the expected public key filename.
if ! GIST_OUTPUT=$(gh gist create --public --desc "$GIST_DESCRIPTION" "$STAGED_KEY" 2>&1); then
    echo "Error: Failed to create gist"
    echo "$GIST_OUTPUT"
    exit 1
fi

GIST_URL=$(printf '%s\n' "$GIST_OUTPUT" | grep -Eo 'https://gist\.github\.com/[^[:space:]]+' | head -1)

if [ -z "$GIST_URL" ]; then
    echo "Error: Failed to create gist"
    exit 1
fi

GIST_URL="${GIST_URL%/}"
GIST_ID="${GIST_URL##*/}"

echo "Gist created: $GIST_URL"
echo ""
echo "You can now use in your config:"
echo "  public_key: github:$USERNAME/gist:$GIST_ID"
echo ""
echo "Current gist URL: $GIST_URL"
