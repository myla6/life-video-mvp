#!/usr/bin/env bash
# Sync life-video-mvp to GitHub. Usage:
#   git-sync.sh              # push only (working tree must be clean)
#   git-sync.sh -m "message"   # add all, commit, push (if there are changes)
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "$ROOT" ]]; then
  echo "ERROR: not a git repository" >&2
  exit 1
fi
cd "$ROOT"

REMOTE="${GIT_REMOTE:-origin}"
BRANCH="${GIT_BRANCH:-main}"
MSG=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -m) MSG="${2:?missing commit message}"; shift 2 ;;
    *) echo "ERROR: unknown argument: $1" >&2; exit 1 ;;
  esac
done

block_secrets() {
  local files="$1"
  while IFS= read -r f; do
    [[ -z "$f" ]] && continue
    case "$f" in
      .env|.env.*|*.pem|*credentials*|*secret*)
        echo "ERROR: refusing to commit sensitive file: $f" >&2
        exit 1
        ;;
    esac
  done <<< "$files"
}

if ! git remote get-url "$REMOTE" &>/dev/null; then
  echo "ERROR: remote '$REMOTE' not configured" >&2
  exit 1
fi

echo "==> Remote: $(git remote get-url "$REMOTE")"
echo "==> Branch: $BRANCH"

if [[ -n "$(git status --porcelain)" ]]; then
  if [[ -z "$MSG" ]]; then
    echo "ERROR: uncommitted changes. Pass -m \"commit message\" to commit and push." >&2
    exit 2
  fi
  git add -A
  staged="$(git diff --cached --name-only)"
  block_secrets "$staged"
  git commit -m "$MSG"
  echo "==> Committed: $MSG"
else
  echo "==> Working tree clean, push only."
fi

echo "==> Pushing..."
git push "$REMOTE" "$BRANCH"
echo "==> Done."
