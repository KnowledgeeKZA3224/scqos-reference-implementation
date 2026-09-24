#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FILE="$ROOT/multicloud/LIVE_CONTINUITY_ANCHOR.json"
[ -s "$FILE" ] || { echo "anchor missing" >&2; exit 2; }
HASH=$(sha256sum "$FILE" | awk "{print \$1}")
az storage blob upload --account-name stscqosc9f1a2b2 --container-name evidence --name "multicloud/continuity/LIVE_CONTINUITY_ANCHOR.json" --file "$FILE" --auth-mode login --overwrite true --only-show-errors -o none
BUCKET=$(aws --profile restored s3api list-buckets --query "Buckets[?contains(Name, \`evidence\`) || contains(Name, \`supreme\`) || contains(Name, \`scqos\`)] | [0].Name" --output text)
[ -n "$BUCKET" ] && [ "$BUCKET" != "None" ] || { echo "No bounded AWS evidence bucket found" >&2; exit 3; }
aws --profile restored s3 cp "$FILE" "s3://$BUCKET/multicloud/continuity/LIVE_CONTINUITY_ANCHOR.json" --only-show-errors
AZ=$(az storage blob download --account-name stscqosc9f1a2b2 --container-name evidence --name "multicloud/continuity/LIVE_CONTINUITY_ANCHOR.json" --file /tmp/scqos-az-anchor.json --auth-mode login --overwrite --only-show-errors >/dev/null && sha256sum /tmp/scqos-az-anchor.json | awk "{print \$1}")
AWS=$(aws --profile restored s3 cp "s3://$BUCKET/multicloud/continuity/LIVE_CONTINUITY_ANCHOR.json" /tmp/scqos-aws-anchor.json --only-show-errors >/dev/null && sha256sum /tmp/scqos-aws-anchor.json | awk "{print \$1}")
[ "$HASH" = "$AZ" ] && [ "$HASH" = "$AWS" ] || { echo "FAIL_CLOSED hash mismatch" >&2; exit 4; }
echo "MULTICLOUD_CONTINUITY_PERMIT $HASH"
