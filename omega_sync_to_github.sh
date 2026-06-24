#!/bin/bash
REPO_DIR="$HOME/omega_sync"
GITHUB_REPO="https://github.com/cipherxsniper/omega-sync.git"

SAFE_FILES=(
  "omega_guardian.sh"
  "omega_start.sh"
  "omega_gallery.html"
  "omega_update_redirect.sh"
  "omega_update_api_url.sh"
  "omega_provenance_api.py"
  "omega_url_broker.py"
  "find2.sh"
  "omega_api_guardian.sh"
)

mkdir -p "$REPO_DIR/phone1"
cd "$REPO_DIR" || exit 1

if [ ! -d ".git" ]; then
  git init
  git remote add origin "$GITHUB_REPO"
  git branch -M main
fi

echo "Copying explicitly listed files..."
count=0
for f in "${SAFE_FILES[@]}"; do
  if [ -f "$HOME/$f" ]; then
    cp "$HOME/$f" "$REPO_DIR/phone1/"
    count=$((count + 1))
  fi
done
echo "Copied $count of ${#SAFE_FILES[@]} listed files"

cp "$HOME"/*.md "$REPO_DIR/phone1/" 2>/dev/null

cd "$REPO_DIR" || exit 1
git add -A
git commit -m "Sync update"
git push -u origin main
echo "Done — https://github.com/cipherxsniper/omega-sync"
