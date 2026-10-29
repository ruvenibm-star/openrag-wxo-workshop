#!/usr/bin/env bash
# Create the reference agent and workflow of Labs 4 to 6 in watsonx Orchestrate, both reading the OpenRAG
# knowledge base through OpenRAG's MCP server. Runs against the active orchestrate CLI environment.
#
#   1. Connection openrag_mcp: key_value, team credentials, in the draft and live environments.
#      Orchestrate sends each entry as an HTTP header on the MCP requests, which gives OpenRAG the
#      x-username and x-api-key headers its docs describe. x-api-key holds the user's password or a
#      Software Hub API key (then x-username is ibmlhapikey_<username>). A basic connection does not
#      work: toolkit creation fails inside Orchestrate with 401 "Invalid authentication credentials".
#   2. Toolkit openrag: remote MCP server <OPENRAG_URL>/mcp over streamable HTTP, importing only
#      openrag_search and openrag_search_knowledge_filters, so the agent cannot change settings or
#      delete documents.
#   3. Agentic workflow policy_answer from policy-answer-workflow.py: openrag_search with the user's
#      Current policies filter, then a generative prompt that writes the answer. Importing it also imports
#      the system tool i__get_flow_status_intrinsic_tool__.
#   4. Agent blue_defence_policy_assistant from blue-defence-policy-assistant.yaml, with a guideline that
#      looks up the Current policies filter for policy questions.
#
# The agent and the workflow see what their Software Hub user sees in OpenRAG: that user's own uploads
# plus shared documents. Use a dedicated user that has ingested the workshop documents and created the
# workshop filters.
#
#   OPENRAG_URL                                     required; also read from secrets/secrets.env
#                                                   one level above the workshop folder
#   OPENRAG_AGENT_USERNAME, OPENRAG_AGENT_PASSWORD  default CPD_USERNAME and CPD_PASSWORD
#
# Usage: orchestrate/setup-agent.sh
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$HERE/../../secrets/secrets.env"
if [ -f "$ENV_FILE" ]; then set -a; . "$ENV_FILE"; set +a; fi
: "${OPENRAG_URL:?Set OPENRAG_URL}"
USERNAME="${OPENRAG_AGENT_USERNAME:-${CPD_USERNAME:?Set OPENRAG_AGENT_USERNAME}}"
PASSWORD="${OPENRAG_AGENT_PASSWORD:-${CPD_PASSWORD:?Set OPENRAG_AGENT_PASSWORD}}"
APP_ID=openrag_mcp
TOOLKIT=openrag

orchestrate connections add -a "$APP_ID" >/dev/null 2>&1 || true
for env in draft live; do
  orchestrate connections configure -a "$APP_ID" --env "$env" --type team --kind key_value
  orchestrate connections set-credentials -a "$APP_ID" --env "$env" -e "x-username=$USERNAME" -e "x-api-key=$PASSWORD"
done

orchestrate toolkits remove -n "$TOOLKIT" >/dev/null 2>&1 || true
orchestrate toolkits add --kind mcp --name "$TOOLKIT" \
  --description "OpenRAG knowledge base for the Blue Defence workshop" \
  --url "$OPENRAG_URL/mcp" --transport streamable_http \
  --tools "openrag_search,openrag_search_knowledge_filters" --app-id "$APP_ID"

CURRENT_POLICIES_FILTER_ID="$(OPENRAG_USERNAME="$USERNAME" OPENRAG_PASSWORD="$PASSWORD" \
  "$HERE/../scripts/openrag.py" filter-id "Current policies")" \
  orchestrate tools import -k flow -f "$HERE/policy-answer-workflow.py"

orchestrate agents import -f "$HERE/blue-defence-policy-assistant.yaml"
orchestrate agents deploy -n blue_defence_policy_assistant
