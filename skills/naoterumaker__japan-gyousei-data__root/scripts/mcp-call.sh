#!/usr/bin/env bash
# MCP server caller for Japanese government open data
# Usage: mcp-call.sh <source> <tool> '<args_json>'
#   source: reinfo | kkj | estat
#   tool: tool name (e.g. reinfolib-real-estate-price)
#   args_json: JSON string of arguments

set -euo pipefail

SOURCE="${1:?Usage: mcp-call.sh <reinfo|kkj|estat> <tool> '<args_json>'}"
TOOL="${2:?Missing tool name}"
ARGS="${3:-\{\}}"

BASE="https://mcp.n-3.ai/mcp?tools="

case "$SOURCE" in
  reinfo)
    URL="${BASE}get-time,reinfolib-real-estate-price,reinfolib-city-list"
    ;;
  kkj)
    URL="${BASE}kkj-search"
    ;;
  estat)
    URL="${BASE}e-stat-get-stats-list,e-stat-get-meta-info,e-stat-get-data-catalog"
    ;;
  *)
    echo "Unknown source: $SOURCE (use reinfo, kkj, or estat)" >&2
    exit 1
    ;;
esac

# Build JSON-RPC payload using jq if available, otherwise printf
if command -v jq &>/dev/null; then
  PAYLOAD=$(jq -nc --arg tool "$TOOL" --argjson args "$ARGS" \
    '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":$tool,"arguments":$args}}')
else
  PAYLOAD="{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/call\",\"params\":{\"name\":\"${TOOL}\",\"arguments\":${ARGS}}}"
fi

# Call MCP server; parse SSE response to extract JSON data
RESPONSE=$(curl -s -X POST "$URL" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "$PAYLOAD" 2>/dev/null)

# SSE responses have "data: " prefix; extract those lines
if echo "$RESPONSE" | grep -q "^data: "; then
  echo "$RESPONSE" | grep "^data: " | sed 's/^data: //'
else
  echo "$RESPONSE"
fi
