#!/usr/bin/env bash
# Session startup / smoke path (harness "clock-in" helper).
# Confirms where you are, surfaces the current state, and checks the repo is consistent.
# Safe to run repeatedly (idempotent). Does NOT start business features — it prepares a session.
set -euo pipefail

echo "=== STORY ENGINE — SESSION INIT ==="
echo "--- pwd ---"
pwd

echo "--- git (last 5) ---"
if [ -d .git ]; then git --no-pager log --oneline -5 2>/dev/null || echo "(no commits yet)"; else echo "(not a git repo yet — 'git init' when ready)"; fi

echo "--- toolchain ---"
command -v uv >/dev/null 2>&1 && echo "uv: $(uv --version)" || echo "uv: NOT FOUND (install: https://docs.astral.sh/uv/)"

echo "--- session handoff (read these) ---"
for f in session_handoff.md PROGRESS.md DECISIONS.md; do
  echo ">>> $f"
  [ -s "$f" ] && sed -n '1,20p' "$f" || echo "  (empty)"
done

echo "--- next feature (WIP=1) ---"
if command -v jq >/dev/null 2>&1 && [ -s feature_list.json ]; then
  jq -r '.features[] | select(.passes==false) | "  [ ] " + .id + " — " + .description' feature_list.json | head -1 || true
else
  echo "  (install jq or read feature_list.json manually)"
fi

echo "--- consistency check ---"
if [ -f pyproject.toml ]; then
  make check || echo "  make check not green yet (expected during initialization)"
else
  echo "  pyproject.toml not created yet — scaffold the project first (see BACKLOG.md)."
fi

echo "=== INIT DONE — work ONE feature, verify, then clock out (update PROGRESS.md + session_handoff.md). ==="
