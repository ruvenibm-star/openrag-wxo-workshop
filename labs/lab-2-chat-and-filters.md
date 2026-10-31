# Lab 2: Chat and retrieval control

20 minutes. You look at the Langflow flow that answers in **Chat**, test it with questions
chose answers sit in tables, slides and spreadsheets, then tune retrieval: a knowledge filter fixes a
conflict between two policy revisions, and the response limit decides which chunks reach the model.

**You need:** Lab 1 finished, so that your knowledge base holds the `blue-defence-knowledge-base` documents. For
step 6, [uv](https://docs.astral.sh/uv/) installed.

## 1. The agent flow in Langflow

**Chat** runs **OpenRAG OpenSearch Agent Flow**, a Langflow flow that the rest of this lab tests and tunes.
**Settings** > **Langflow** > **Agent** > **Edit in Langflow** opens it in Langflow, at
<https://openrag-lf-cpd.apps.itz-lfbzmf.infra01-lb.tok04.techzone.ibm.com>. The editor saves the flow within seconds and drops the binding of the Text Input below, and
**Chat** then ignores knowledge filters, which steps 4 and 5 use. The flow looks like this:

![The OpenRAG OpenSearch Agent Flow in Langflow](images/lab-2/langflow-agent-flow.png)

| Part of the flow | What it does |
|---|---|
| Agent | The language model with the system prompt. It decides on each turn whether to call a tool. |
| OpenSearch (Multi-Model Multi-Embedding) | Hybrid search over your chunks, offered to the agent as the tools `search_documents` and `raw_search`. The agent writes the search query itself. |
| Embedding Model (three of them) | Embed the agent's query with the model that embedded the chunks. |
| Text Input | Carries the knowledge filter selected in **Chat** (data sources, response limit, score threshold) into the OpenSearch component's **Search Filters (JSON)** input (`filter_expression`) and into the Prompt Template. OpenRAG fills it on each request through the global variable `OPENRAG-QUERY-FILTER`, so the editor shows it empty. |
| Prompt Template | Adds the selected knowledge filter to the agent's input. |
| Other tools | MCP Tools (the URL ingestion flow), the Calculator, and a search tool added for a separate demo. |

The system prompt tells the agent to retrieve when unsure, to cite chunk IDs, and to say "No relevant
supporting sources were found" when nothing matches. 

## 2. Ask questions across formats

Open **Chat** and ask each question.

| Question | Answer contains | From |
|---|---|---|
| What torque should the Sentinel-7 propulsion pod mounting bolts be tightened to? | 85 N·m | Torque table on page 2 of the maintenance manual (PDF) |
| What is Blue Defence's policy on working from home? | That no source covers it, in wording that varies: "No relevant supporting sources were found" or "could not be found in the provided search results" | No document covers it |

The last question checks that the agent says it has no source instead of inventing an answer.

Under each answer:

- Click a source card to see the chunk it came from, with its page, score, parser and chunking settings.
- Expand **Function Call: search_documents** to see the query the agent wrote (for the torque question,
  `Sentinel-7 propulsion pod mounting bolts torque`) and every chunk the search returned, with its file,
  page and score.

![The torque answer with its source chunk](images/lab-2/chat-torque-citation.jpg)

![The search_documents call with the agent's query and the returned chunks](images/lab-2/chat-function-call.jpg)

![Asking in Chat, opening the source card and the function call](images/lab-2/chat-citation.gif)


---

Next: [Lab 3: Agents over MCP](lab-3-agents-over-mcp.md)
