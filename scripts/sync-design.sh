#!/usr/bin/env bash
# Stáhne aktuální tokeny a loga z (privátního) repa skvscb-design do design/ a zapíše verzi.
# Vyžaduje přihlášené GitHub CLI: gh auth login
set -euo pipefail
cd "$(dirname "$0")/.."
REF="${1:-main}"
REPO="jakubbican/skvscb-design"
get() { gh api "repos/$REPO/contents/$1?ref=$REF" -H "Accept: application/vnd.github.raw" > "$2"; }
mkdir -p design/logo design/partneri
get tokens/tokens.css design/tokens.css
for f in logo-navy.svg logo-white.svg logo-oval-vysivka.svg; do get "logo/$f" "design/logo/$f"; done
for f in $(gh api "repos/$REPO/contents/partneri?ref=$REF" --jq '.[].name'); do get "partneri/$f" "design/partneri/$f"; done
gh api "repos/$REPO/contents/tokens/tokens.json?ref=$REF" -H "Accept: application/vnd.github.raw" | python3 -c 'import json,sys; print(json.load(sys.stdin)["version"])' > design/DESIGN_VERSION
echo "design $(cat design/DESIGN_VERSION) synced from $REPO@$REF"
