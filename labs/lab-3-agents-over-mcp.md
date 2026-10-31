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

### 3. Search OpenRAG through MCP

Now that we have confirmed the MCP connection and can see the tools exposed by OpenRAG, let's call one of those tools directly.

We'll use `openrag_search` to ask a natural-language question:

> **What is Blue Defence's policy on working from home?**

Run:

```bash
scripts/mcp-client.py call openrag_search '{"query": "Blue Defence work from home remote working policy", "limit": 3}'
```

The search returns the highest-ranked chunks from the OpenRAG knowledge base, together with information such as the source document, page and relevance score.

Here we're interacting with OpenRAG through its MCP interface rather than through the UI. I'm calling the search tool directly and passing it a natural-language question.

What comes back isn't the final generated answer. OpenRAG returns the relevant chunks, including the source document and relevance score. An agent can then use this retrieved context to formulate its response.

In this example, we can also see an important characteristic of retrieval. OpenRAG returns the chunks that it considers most relevant to our query, but that does not necessarily mean those chunks contain enough information to answer the question.

This is why grounding is important. The agent consuming these results needs to reason over the retrieved information and determine whether there is sufficient evidence to answer the user's question, rather than simply generating an answer regardless of what was retrieved.

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
