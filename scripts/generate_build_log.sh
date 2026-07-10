#!/usr/bin/env bash
set -e
STATUS_LIST=(success success success failed)
STATUS=${STATUS_LIST[$RANDOM % ${#STATUS_LIST[@]}]}
DURATION=$((30 + RANDOM % 180))
FAILED_TESTS=0
if [ "$STATUS" = "failed" ]; then
  FAILED_TESTS=$((1 + RANDOM % 5))
fi
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "$TIMESTAMP,$STATUS,$DURATION,$FAILED_TESTS"
