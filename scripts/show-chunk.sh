#!/usr/bin/env bash
# Show how OpenRAG stores a document's chunks in OpenSearch, for Lab 1 step 6: the chunk index's field
# types, then one chunk of the named file with each vector shortened to its length. Reads opensearch637
# from inside a coordinating pod with the admin credentials. Needs oc access to the cluster's cpd namespace.
#
#   INDEX     chunk index (default orag-documents)
#   KUBECONFIG                 the cluster's kubeconfig, if not oc's default
#
# Usage: scripts/show-chunk.sh [filename] [page]     default sentinel-7-maintenance-manual.pdf, page 2
set -euo pipefail

NS=cpd
OS_CR=opensearch637
INDEX="${INDEX:-orag-documents}"
FILE="${1:-sentinel-7-maintenance-manual.pdf}"
PAGE="${2:-2}"

OS_USER="$(oc -n "$NS" get secret "$OS_CR-admin-password" -o jsonpath='{.data.username}' | base64 -d)"
OS_PASS="$(oc -n "$NS" get secret "$OS_CR-admin-password" -o jsonpath='{.data.password}' | base64 -d)"
OS_POD="$(oc -n "$NS" get pods -l "opster.io/opensearch-cluster=$OS_CR,opster.io/opensearch-nodepool=coordinating" -o json |
  jq -r '[.items[] | select(.metadata.deletionTimestamp == null and ([.status.containerStatuses[]?.ready] | all))][0].metadata.name // empty')"
[ -n "$OS_POD" ] || { echo "No ready coordinating pod" >&2; exit 1; }
# osapi <path> [curl args]: the credentials go to curl over stdin, ahead of any request body (-d @-).
osapi() {
  local body=false a
  for a in "$@"; do [ "$a" != @- ] || body=true; done
  { printf '%s\n' "$OS_USER:$OS_PASS"; if $body; then cat; fi; } |
    oc -n "$NS" exec -i "$OS_POD" -c opensearch -- bash -c 'IFS= read -r auth
      exec curl -sk --fail-with-body -K <(printf "user = \"%s\"\n" "$auth") -H "Content-Type: application/json" "$@"' \
      _ "https://localhost:9200$1" "${@:2}"
}

echo "== $INDEX fields"
osapi "/$INDEX/_mapping" | jq -r --arg i "$INDEX" '.[$i].mappings.properties | to_entries[] |
  "\(.key)\t\(.value.type // "object")" + (if .value.type == "knn_vector"
    then "\t\(.value.dimension) dimensions, \(.value.method.name) on \(.value.method.engine), \(.value.method.space_type)" else "" end)' |
  column -t -s $'\t'

echo
echo "== One chunk of $FILE, page $PAGE"
jq -n --arg f "$FILE" --argjson p "$PAGE" \
  '{size: 1, query: {bool: {filter: [{term: {filename: $f}}, {term: {page: $p}}]}}}' |
  osapi "/$INDEX/_search" -d @- |
  jq '.hits.hits[0]._source // error("no chunk of that file and page") | with_entries(
    if (.value | type) == "array" and (.value | length) > 20 then .value = "[\(.value | length) numbers]" else . end)'
