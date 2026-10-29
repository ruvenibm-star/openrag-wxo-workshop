#!/usr/bin/env bash
# Run every lab step that can be scripted against the live OpenRAG instance, in lab order, and check
# each answer against answer-key.yaml. Run it the day before the workshop.
#
#   1. reset: delete the workshop documents and filters, restore the instance's ingestion settings
#   2. Lab 1: ingest blue-defence-knowledge-base/; turn OCR off and ingest the scanned memo (it must fail),
#      then turn OCR back on and ingest it again (it must succeed)
#   3. Lab 2: ask the kb questions, apply the knowledge filters in filters/, ask the filters
#      questions
#   4. Lab 3: connect over MCP and call openrag_search and openrag_chat with the Current policies filter
#   5. Labs 4 and 5: ask the reference Orchestrate agent that orchestrate/setup-agent.sh creates
#      one question, and evaluate it with the test cases in orchestrate/tests/
#
# A failed answer check or agent call does not stop the run; the script exits 1 at the end if any
# of them failed.
#
# Leaves the instance in the state the labs end in: all sample documents ingested (the memo with
# OCR), the workshop filters present, OCR on.
#
# Usage: scripts/rehearse.sh [--keep]     --keep skips the reset
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
WS="$HERE/.."
O="$HERE/openrag.py"
MEMO="$WS/sample-docs/scanned/site-inspection-memo-2026-08-14.pdf"
step() { printf '\n== %s\n' "$*"; }
FAILED=()
check() { "$O" check --group "$1" || FAILED+=("$1"); }

if [ "${1:-}" != "--keep" ]; then
  step "Reset"
  "$O" reset
fi

step "Lab 1: ingest the knowledge base folder"
"$O" ingest "$WS/sample-docs/blue-defence-knowledge-base"

step "Lab 1: scanned memo with OCR off (expected to fail)"
"$O" settings ocr=false >/dev/null
if "$O" ingest "$MEMO"; then
  echo "The memo ingested with OCR off; expected 'No text content could be extracted from document'" >&2
  exit 1
fi
check ocr-off

step "Lab 1: scanned memo with OCR on"
"$O" settings ocr=true >/dev/null
"$O" ingest "$MEMO"
check ocr

step "Lab 2: questions over the whole knowledge base"
check kb

step "Lab 2: knowledge filters"
"$O" filter-apply "$WS"/filters/*.json
check filters

step "Lab 3: MCP client"
"$HERE/mcp-client.py" smoke

step "Lab 4: reference Orchestrate agent"
"$WS/orchestrate/ask-agent.sh" "What torque should the Sentinel-7 propulsion pod mounting bolts be tightened to?" ||
  FAILED+=("orchestrate (run orchestrate/setup-agent.sh first)")

step "Lab 5: evaluate the Orchestrate agent"
"$WS/orchestrate/evaluate-agent.sh" || FAILED+=("evaluation")

step "Rehearsal complete"
"$O" files
if [ ${#FAILED[@]} -gt 0 ]; then
  echo "Answer checks failed in: ${FAILED[*]}" >&2
  exit 1
fi
