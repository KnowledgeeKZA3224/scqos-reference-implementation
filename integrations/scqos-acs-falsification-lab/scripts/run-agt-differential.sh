#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${ACS_SOURCE_DIR:?Set ACS_SOURCE_DIR to a checkout of GenAI-Security-Project/agent-control-standard}"
export PATH="${HOME}/.bun/bin:${PATH}"
AGT="${ACS_SOURCE_DIR}/reference-implementations/agt"
cd "$AGT"
bun install --frozen-lockfile
ACS_GUARDIAN_PORT=18787 bun run guardian > /tmp/scqos-acs-agt.log 2>&1 &
pid=$!
trap 'kill "$pid" 2>/dev/null || true' EXIT
sleep 2
cd - >/dev/null
. .venv/bin/activate
set +e
python -m scqos_acs_lab.harness --endpoint http://127.0.0.1:18787/acs --output run-evidence/agt-reference.json
code=$?
set -e
python scripts/summarize_evidence.py
exit "$code"
