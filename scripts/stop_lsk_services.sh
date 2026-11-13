#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
for name in gateway sales marketing finance; do
  pidfile="$ROOT/.run-lsk/$name.pid"
  if [[ -f "$pidfile" ]]; then
    pid="$(cat "$pidfile")"
    if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid"
      echo "Stopped $name (pid $pid)"
    else
      echo "$name was not running"
    fi
    rm -f "$pidfile"
  fi
done
