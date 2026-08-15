#!/usr/bin/env bash
#
# Commit local changes and push them to GitHub.
#
# Triggered by chrysanthemum-sync.path when songs/ changes, and by
# chrysanthemum-sync.timer as a backstop for anything the watcher misses or
# a push that failed earlier (say, the network was down).
#
# Exits 0 when there is nothing to do, so a quiet timer tick is not an error.

set -euo pipefail

REPO=/workspace
BRANCH=main
cd "$REPO"

# Let a burst of edits settle rather than committing a half-saved file.
sleep 5

if [[ -z "$(git status --porcelain)" ]]; then
  # Nothing local, but an earlier push may still be stranded.
  git fetch -q origin "$BRANCH" || exit 0
  if [[ -n "$(git rev-list "origin/$BRANCH..$BRANCH" 2>/dev/null)" ]]; then
    echo "no local edits, but unpushed commits exist — pushing"
    git push origin "$BRANCH"
  fi
  exit 0
fi

# Regenerate the site so the committed HTML matches the sources. If build.py
# rejects a song, set -e aborts here and nothing is committed or pushed.
echo "rebuilding"
python3 build.py

if [[ -z "$(git status --porcelain)" ]]; then
  echo "nothing to commit after rebuild"
  exit 0
fi

# Summarise what changed, for the commit subject.
mapfile -t changed < <(git status --porcelain | awk '{print $NF}' | grep '^songs/' | xargs -r -n1 basename | sed 's/\.md$//')
if [[ ${#changed[@]} -gt 0 ]]; then
  subject="Update $(IFS=', '; echo "${changed[*]}")"
  # Keep the subject to a sane length.
  (( ${#subject} > 68 )) && subject="Update ${#changed[@]} songs"
else
  subject="Update site"
fi

git add -A
git commit -q -m "$subject" -m "Committed automatically by chrysanthemum-sync."
echo "committed: $subject"

# Integrate anything pushed from elsewhere before we push.
if ! git pull --rebase --autostash -q origin "$BRANCH"; then
  echo "rebase onto origin/$BRANCH failed — leaving the commit unpushed" >&2
  git rebase --abort 2>/dev/null || true
  exit 1
fi

git push -q origin "$BRANCH"
echo "pushed to origin/$BRANCH"
