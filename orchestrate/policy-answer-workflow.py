"""Agentic workflow policy_answer, the reference for Lab 4: search OpenRAG over MCP with the Current policies
knowledge filter, then write the answer from the returned chunks with a generative prompt.

    question -> Call a tool: openrag:openrag_search (query = question, limit 5, filter_id = Current policies)
             -> generative prompt: write the answer from the chunks, naming the file of each fact
             -> answer

orchestrate/setup-agent.sh imports it with
`orchestrate tools import -k flow -f orchestrate/policy-answer-workflow.py`, after the openrag toolkit
exists, with CURRENT_POLICIES_FILTER_ID set to the id of the agent user's Current policies filter
(`scripts/openrag.py filter-id "Current policies"`).
"""

import os

from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.flows import END, Flow, flow, START

FILTER_ID = os.environ["CURRENT_POLICIES_FILTER_ID"]


class Question(BaseModel):
    question: str = Field(description="A question about Blue Defence policies")


class Answer(BaseModel):
    answer: str = Field(description="The answer, naming the file each fact comes from")


class AnswerInput(BaseModel):
    question: str = Field(description="The user's question")
    chunks: str = Field(description="Chunks returned by OpenRAG search")


@flow(
    name="policy_answer",
    display_name="Policy answer",
    description="Answers a question about Blue Defence policies in force from the OpenRAG "
                "knowledge base, leaving out superseded revisions, and names the source file.",
    input_schema=Question,
    output_schema=Answer,
)
def build_policy_answer(aflow: Flow) -> Flow:
    search = aflow.tool("openrag:openrag_search", name="search_openrag")
    search.map_input(input_variable="query", expression="flow.input.question")
    search.map_input(input_variable="limit", expression="5")
    search.map_input(input_variable="filter_id", expression=f'"{FILTER_ID}"')

    write = aflow.prompt(
        name="write_answer",
        display_name="Write the answer from the chunks",
        description="Write an answer to the question using only the supplied chunks.",
        system_prompt=[
            "You answer questions about Blue Defence policies.",
            "Use only the supplied chunks. Name the file each fact comes from.",
            "If the chunks do not contain the answer, say that the knowledge base has no information on it.",
        ],
        user_prompt=["Question: {question}", "Chunks: {chunks}"],
        llm="groq/openai/gpt-oss-120b",
        input_schema=AnswerInput,
        output_schema=Answer,
    )
    write.map_input(input_variable="question", expression="flow.input.question")
    write.map_input(input_variable="chunks", expression="flow.search_openrag.output")

    aflow.sequence(START, search, write, END)
    aflow.map_output(output_variable="answer", expression="flow.write_answer.output.answer")
    return aflow
