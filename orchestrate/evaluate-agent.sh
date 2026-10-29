#!/usr/bin/env bash
# Evaluate a watsonx Orchestrate agent against the Lab 5 test cases in tests/: a simulated user asks each
# starting sentence, and the evaluation checks the tool calls the agent makes and the facts in its answer.
# Runs against the active orchestrate CLI environment.
#
#   tests/clearance-validity.json  must look up the Current policies filter and search with its id; 5 years
#   tests/bolt-torque.json         must search; 85 N·m
#   tests/working-from-home.json   must search; says the knowledge base has no information
#
# The cases name tools by their MCP names (openrag_search, not openrag:openrag_search); with the toolkit
# prefix no tool call matches. CURRENT_POLICIES_FILTER_ID in the clearance case is replaced with the id of the
# Current policies filter of the OpenRAG user the openrag toolkit signs in as.
#
# The evaluation commands need the ADK's agentops extra, which this script runs through uvx on Python 3.12
# (ibm-watsonx-orchestrate[agentops]==2.19.1), so the installed ADK is left unchanged. The simulated user and
# the judge run through the Orchestrate instance's AI gateway; no other credentials are needed. The three
# cases take under a minute.
#
#   OPENRAG_AGENT_USERNAME, OPENRAG_AGENT_PASSWORD  default CPD_USERNAME and CPD_PASSWORD
#   OUT                                             results directory (default a new temporary directory)
#
# Usage: orchestrate/evaluate-agent.sh [agent_name]      default blue_defence_policy_assistant
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$HERE/../../secrets/secrets.env"
if [ -f "$ENV_FILE" ]; then set -a; . "$ENV_FILE"; set +a; fi
AGENT="${1:-blue_defence_policy_assistant}"
OUT="${OUT:-$(mktemp -d)}"
mkdir -p "$OUT"
CASES="$(mktemp -d)"
trap 'rm -rf "$CASES"' EXIT

FILTER_ID="$(OPENRAG_USERNAME="${OPENRAG_AGENT_USERNAME:-${CPD_USERNAME:-}}" \
  OPENRAG_PASSWORD="${OPENRAG_AGENT_PASSWORD:-${CPD_PASSWORD:-}}" \
  "$HERE/../scripts/openrag.py" filter-id "Current policies")"
for f in "$HERE"/tests/*.json; do
  jq --arg agent "$AGENT" --arg id "$FILTER_ID" '.agent = $agent
    | (.goal_details[] | select(.args.filter_id == "CURRENT_POLICIES_FILTER_ID") | .args.filter_id) = $id' \
    "$f" > "$CASES/$(basename "$f")"
done

echo "Evaluating $AGENT with $(ls "$CASES" | wc -l | tr -d ' ') cases; results in $OUT"
uvx --python 3.12 --from 'ibm-watsonx-orchestrate[agentops]==2.19.1' \
  orchestrate evaluations evaluate -p "$CASES" -o "$OUT" > "$OUT/evaluate.log" 2>&1 ||
  { tail -20 "$OUT/evaluate.log" >&2; exit 1; }

SUMMARY="$(ls -t "$OUT"/*/summary_metrics.csv | head -1)"
python3 - "$SUMMARY" <<'EOF'
import csv, sys
rows = list(csv.DictReader(open(sys.argv[1])))
print(f"{'case':<20} {'journey':<8} {'recall':>6} {'precision':>9} {'text':>5} {'time (s)':>8}")
for r in rows:
    print(f"{r['dataset_name']:<20} {'pass' if r['is_success'] == 'True' else 'FAIL':<8} {float(r['tool_call_recall']):>6.2f}"
          f" {float(r['tool_call_precision']):>9.2f} {float(r['text_match']):>5.2f} {float(r['average_agent_response_time']):>8.1f}")
passed = sum(r["is_success"] == "True" for r in rows)
print(f"\n{passed}/{len(rows)} journeys succeeded")
sys.exit(0 if rows and passed == len(rows) else 1)
EOF
