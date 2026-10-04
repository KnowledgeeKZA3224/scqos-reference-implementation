#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
. .venv/bin/activate
pytest -q
python -m scqos_acs_lab.harness --direct-local --output run-evidence/local.json
python -m scqos_acs_lab.harness --direct-local --live-scqos --output run-evidence/live-scqos.json
python -m scqos_acs_lab.side_effect --live-scqos --output run-evidence/cloud-to-terminal.json
python scripts/make-summary.py
