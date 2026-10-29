# Lab 3: Agents over MCP

20 minutes. You call OpenRAG's MCP tools the way an agent does, with your own account and
your own Lab 2 filter: search, look up a knowledge filter, and search with it. This lab ends the OpenRAG part
of the workshop; Labs 4 to 6 build agents in watsonx Orchestrate on these tools.

**You need:** Labs 1 and 2 finished, and [uv](https://docs.astral.sh/uv/) installed.

## 1. The MCP endpoint

| Setting | Value |
|---|---|
| Endpoint | `https://openrag-fe-cpd.apps.itz-lfbzmf.infra01-lb.tok04.techzone.ibm.com/mcp` |
| Transport | Streamable HTTP |
| Authentication | Headers `x-username` and `x-api-key` |
| `x-api-key` | Your password, or a Software Hub API key (then `x-username` is `ibmlhapikey_<username>`) |

The route serves a publicly trusted certificate on the workshop cluster. On a cluster that signs routes
with the internal Software Hub CA, the client must trust that CA first (see "Retrieving OpenRAG
certificates" in the watsonx.data documentation).

## 2. List the tools

```bash
export OPENRAG_URL=https://openrag-fe-cpd.apps.itz-lfbzmf.infra01-lb.tok04.techzone.ibm.com
export OPENRAG_USERNAME=<username> OPENRAG_PASSWORD=<password>
scripts/mcp-client.py tools
```

The server identifies itself as `OpenRAG 3.2.4` and lists 17 tools:

| Reads | Changes |
|---|---|
| `openrag_search`, `openrag_chat`, `openrag_list_chats`, `openrag_get_chat` | `openrag_delete_chat` |
| `openrag_search_knowledge_filters`, `openrag_get_knowledge_filter` | `openrag_create_knowledge_filter`, `openrag_update_knowledge_filter`, `openrag_delete_knowledge_filter` |
| `openrag_get_settings`, `openrag_list_models` | `openrag_update_settings` |
| `openrag_get_task_status`, `openrag_get_task_status_enhanced`, `openrag_list_tasks_enhanced` | `openrag_delete_document` |

An agent connected with all tools can change the instance's models and prompts, and delete documents,
with the rights of the account it signs in as.

## 3. Search, then search with a filter

1. Search for the SECRET clearance validity without a filter:

   ```bash
   scripts/mcp-client.py call openrag_search '{"query": "SECRET security clearance validity", "limit": 3}'
   ```

   Chunks of both revisions come back with almost the same score: `security-clearance-policy-2026.docx` and the
   superseded `security-clearance-policy-2024.docx`. As in Lab 2 step 3, search cannot tell which one is current.
2. Look up your `Current policies` filter and note its `id`:

   ```bash
   scripts/mcp-client.py call openrag_search_knowledge_filters '{"query": "Current policies"}'
   ```

3. Search again with that id:

   ```bash
   scripts/mcp-client.py call openrag_search '{"query": "SECRET security clearance validity", "limit": 3, "filter_id": "<id>"}'
   ```

   Only chunks of the documents in force come back, with `security-clearance-policy-2026.docx` first.

These are the two calls the Orchestrate agents in Labs 4 to 6 make: look up the filter, then search with its
id. Each result carries the chunk's text, file, page and score, and the agent's own model writes the answer
from them.

## Points to discuss

- An MCP client sees what its OpenRAG account sees: that account's own uploads plus shared documents.
  Production agents need a dedicated account that holds, or is shared, the documents they should use.
- Give an agent only the tools it needs. The Orchestrate toolkit in Lab 4 holds `openrag_search` and
  `openrag_search_knowledge_filters`, both read-only, so its agents cannot change settings or delete
  documents even though the account could.
- `openrag_search` returns chunks and lets the agent's own model write the answer; `openrag_chat` returns
  OpenRAG's answer. Search suits agents that combine several sources; chat suits a thin client.

---

Next: [Lab 4: Build a low-code agent](lab-4-low-code-agent.md)
