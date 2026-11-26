#!/usr/bin/env bash
# Copy the shareable parts of this repo (engine + problems) into a checkout
# of the public template repo, leaving personal progress behind.
#
# Usage: scripts/export_template.sh <path-to-template-checkout>
# Then review, commit and push from inside that checkout.
set -euo pipefail

DEST="${1:?usage: scripts/export_template.sh <path-to-template-checkout>}"
SRC="$(cd "$(dirname "$0")/.." && pwd)"

[ -d "$DEST/.git" ] || { echo "error: $DEST is not a git checkout"; exit 1; }
[ "$(cd "$DEST" && pwd)" != "$SRC" ] || { echo "error: destination is this repo"; exit 1; }

# --delete mirrors removals too; the excluded paths are never touched in DEST.
rsync -a --delete \
  --exclude '.git/' \
  --exclude '.venv/' \
  --exclude '__pycache__/' \
  --exclude '.claude/' \
  --exclude '.DS_Store' \
  --exclude '*.duckdb' \
  --exclude '*.duckdb.wal' \
  --exclude 'progress/profile.md' \
  --exclude 'progress/attempts.jsonl' \
  --exclude 'solutions/*.sql' \
  --exclude 'problems/u*/' \
  "$SRC/" "$DEST/"

echo "Exported to $DEST."

# Flag any file that still mentions the learner's name from progress/profile.md.
NAME="$(sed -n 's/^- \*\*Name:\*\* *//p' "$SRC/progress/profile.md" 2>/dev/null | head -1)"
if [ -n "$NAME" ] && [ "$NAME" != "—" ]; then
  HITS="$(grep -rIlw -i --exclude-dir=.git -- "$NAME" "$DEST" || true)"
  if [ -n "$HITS" ]; then
    echo "WARNING: these files mention '$NAME' — fix before pushing:"
    echo "$HITS"
    exit 1
  fi
  echo "Personal-data check passed (no mention of '$NAME')."
fi
