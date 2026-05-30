#!/usr/bin/env bash
set -euo pipefail

message="${1:-Approval needed in the Codex app.}"

osascript \
  -e 'on run argv' \
  -e 'display dialog (item 1 of argv) with title "Codex needs you" buttons {"OK"} default button "OK" giving up after 60' \
  -e 'end run' \
  "$message"
