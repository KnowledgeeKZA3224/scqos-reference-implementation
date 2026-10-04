#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p upstream
if [[ ! -d upstream/agent-control-standard/.git ]]; then
  git clone --filter=blob:none https://github.com/GenAI-Security-Project/agent-control-standard.git upstream/agent-control-standard
fi
if [[ ! -d upstream/agent-evidence-vectors/.git ]]; then
  git clone --filter=blob:none https://github.com/probityai/agent-evidence-vectors.git upstream/agent-evidence-vectors
fi
git -C upstream/agent-control-standard fetch origin 27799c2c27414a483a4a043b957bfd2997d53231
git -C upstream/agent-control-standard checkout --detach 27799c2c27414a483a4a043b957bfd2997d53231
git -C upstream/agent-evidence-vectors fetch origin bbdef583c9241138e5c2b5d872bc77f7f539e9ac
git -C upstream/agent-evidence-vectors checkout --detach bbdef583c9241138e5c2b5d872bc77f7f539e9ac
printf 'ACS=%s\nVECTORS=%s\n' "$(git -C upstream/agent-control-standard rev-parse HEAD)" "$(git -C upstream/agent-evidence-vectors rev-parse HEAD)"
