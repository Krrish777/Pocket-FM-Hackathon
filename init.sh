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

echo "--- EXT-1 corpus state (scraper branch) ---"
# The corpus is the handoff artifact the knowledge base ingests, so its schema version and partiality
# are session-start facts, not something to rediscover mid-task. data/raw/ is gitignored, so a fresh
# clone legitimately has no corpora — absence here is not an error.
sink="src/story_engine/adapters/outbound/fanfic/jsonl_sink.py"
if [ -f "$sink" ]; then
  echo "  corpus schema (code is authoritative): $(sed -n 's/^CORPUS_SCHEMA_VERSION = "\(.*\)"/\1/p' "$sink")"
  echo "  contract doc: docs/EXT-1-scraper-output-contract.md"
fi
if [ -d data/raw/fanfic ]; then
  for m in data/raw/fanfic/*/manifest.json; do
    [ -e "$m" ] || continue
    if command -v jq >/dev/null 2>&1; then
      echo "  $(dirname "$m"): $(jq -r '"\(.story_count) works, \(.chapter_count) chapters, \(.total_words) words, schema \(.schema_version)"' "$m")"
    else
      echo "  $(dirname "$m") (install jq for a summary)"
    fi
  done
else
  echo "  (no local corpora — run: uv run story-engine harvest \"Dexter\" --kind novel)"
fi

echo "--- consistency check ---"
# The gate's exit code is the signal, so it must NOT be swallowed. This previously ended in
# `|| echo "not green yet (expected during initialization)"`, which made init.sh exit 0 on a RED
# gate — the same failure mode as piping `make check` into grep/tail. Initialization is over: a red
# gate is now a real defect and must stop the session.
if [ -f pyproject.toml ]; then
  if make check; then
    echo "  consistency: GREEN"
  else
    status=$?
    echo "  consistency: RED (make check exited ${status}) — FIX THIS BEFORE WORKING." >&2
    exit "${status}"
  fi
else
  echo "  pyproject.toml not created yet — scaffold the project first (see BACKLOG.md)."
fi

echo "=== INIT DONE — work ONE feature, verify, then clock out (update PROGRESS.md + session_handoff.md). ==="
