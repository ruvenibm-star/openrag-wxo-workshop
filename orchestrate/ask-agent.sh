#!/usr/bin/env bash
# Ask the reference agent (Lab 4) one question through the watsonx Orchestrate chat completions API and print the
# answer. Signs in to IBM Cloud IAM with WXO_APIKEY and calls WXO_URL, both from the environment or from
# secrets/secrets.env one level above the workshop folder.
#
#   POST https://iam.cloud.ibm.com/identity/token                         API key -> bearer token
#   GET  <WXO_URL>/v1/orchestrate/agents?names=<agent>                    agent id
#   POST <WXO_URL>/v1/orchestrate/<agent_id>/chat/completions             {messages, stream: false}
#
# Usage: orchestrate/ask-agent.sh "<question>" [agent_name]
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$HERE/../../secrets/secrets.env"
if [ -f "$ENV_FILE" ]; then set -a; . "$ENV_FILE"; set +a; fi
QUESTION="${1:?Usage: $0 \"<question>\" [agent_name]}"
AGENT="${2:-blue_defence_policy_assistant}"
: "${WXO_URL:?Set WXO_URL}" "${WXO_APIKEY:?Set WXO_APIKEY}"

TOKEN="$(curl -sS -X POST https://iam.cloud.ibm.com/identity/token \
  --data-urlencode grant_type=urn:ibm:params:oauth:grant-type:apikey --data-urlencode "apikey=$WXO_APIKEY" | jq -r .access_token)"
AGENT_ID="$(curl -sS -H "Authorization: Bearer $TOKEN" "$WXO_URL/v1/orchestrate/agents?names=$AGENT" | jq -r '.[0].id // empty')"
[ -n "$AGENT_ID" ] || { echo "No agent named $AGENT in $WXO_URL" >&2; exit 1; }

curl -sS -m 300 -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -X POST "$WXO_URL/v1/orchestrate/$AGENT_ID/chat/completions" \
  -d "$(jq -n --arg q "$QUESTION" '{stream: false, messages: [{role: "user", content: $q}]}')" |
  jq -r '.choices[0].message.content // .'
