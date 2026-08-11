#!/usr/bin/env bash
set -euo pipefail

marketplace_url="https://github.com/ianyu1201/project-delivery-suite"
plugin_ref="project-delivery-suite@project-delivery-suite"

if ! command -v codex >/dev/null 2>&1; then
  echo "Codex CLI is required before installing this plugin." >&2
  exit 1
fi

codex plugin marketplace add "$marketplace_url"
codex plugin add "$plugin_ref"

echo "Installed $plugin_ref. Start a new Codex task to load both Skills."
