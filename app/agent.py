"""LangChain tutor agent with required function-calling tools (per-user memory)."""
from __future__ import annotations

import json
import threading
from typing import Callable

from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI

from app.config import (
    OPENAI_API_KEY,
    TUTOR_LLM_TIMEOUT,
    TUTOR_MAX_AGENT_ITERATIONS,
    TUTOR_MAX_OUTPUT_TOKENS,
    TUTOR_MODEL,
)
from app.memory_store import format_memory_hits, get_memory_store


def _make_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=TUTOR_MODEL,
        api_key=OPENAI_API_KEY or None,
        temperature=0.25,
        timeout=float(TUTOR_LLM_TIMEOUT),
        max_retries=1,
        max_tokens=TUTOR_MAX_OUTPUT_TOKENS,
    )


def build_tools(
    user_id: int,
    quiz_llm_factory: Callable[[], ChatOpenAI] | None = None,
    diagram_llm_factory: Callable[[], ChatOpenAI] | None = None,
    summarize_llm_factory: Callable[[], ChatOpenAI] | None = None,
):
    store = get_memory_store(user_id)
    quiz_llm = (quiz_llm_factory or _make_llm)()
    diagram_llm = (diagram_llm_factory or _make_llm)()
    summary_llm = (summarize_llm_factory or _make_llm)()

    def generate_quiz(topic: str) -> str:
        """Generate a short quiz (MCQ + one short answer) for the given topic."""
        prompt = (
            "Create a study quiz as JSON with keys: "
            'topic, questions (list of {id, question, choices (optional), answer, explanation}). '
            "Use 3-5 questions. Only output valid JSON, no markdown."
            f"\nTopic: {topic}"
        )
        out = quiz_llm.invoke(prompt)
        return out.content if hasattr(out, "content") else str(out)

    def save_memory(data: str) -> str:
        """Persist durable notes. Start lines with WEAKNESS:, GOAL:, or STRENGTH: so the tutor prioritizes them later."""
        d = data.strip()
        meta: dict = {"kind": "tutor_note"}
        u = d.upper()
        if u.startswith("WEAKNESS:"):
            meta["kind"] = "weakness"
        elif u.startswith("GOAL:"):
            meta["kind"] = "goal"
        elif u.startswith("STRENGTH:"):
            meta["kind"] = "strength"
        mid = store.add_text(d, metadata=meta)
        return json.dumps({"saved": True, "memory_id": mid})

    def retrieve_memory(query: str) -> str:
        """Retrieve past memories and notes relevant to the query (weaknesses, preferences, history)."""
        hits = store.search(query, k=6)
        return format_memory_hits(hits) if hits else "[]"

    def summarize_document(file: str) -> str:
        """Summarize document text from the learner (sections, key ideas, definitions)."""
        text = file.strip()
        if len(text) > 12000:
            text = text[:12000] + "\n...[truncated]"
        msg = (
            "Summarize for a student. Use: Title, Key points (bullets), "
            "Important terms, 2 practice questions. Be concise.\n\n" + text
        )
        out = summary_llm.invoke(msg)
        return out.content if hasattr(out, "content") else str(out)

    def generate_diagram(topic: str) -> str:
        """Emit a Mermaid diagram string (flowchart or sequence) that helps explain the topic."""
        prompt = (
            "Output ONLY a Mermaid code block content (no ``` fences) for a simple diagram "
            "explaining the topic for students. Prefer flowchart TD. Max ~15 nodes.\nTopic: "
            + topic
        )
        out = diagram_llm.invoke(prompt)
        raw = out.content if hasattr(out, "content") else str(out)
        return raw.strip()

    return [
        StructuredTool.from_function(generate_quiz, name="Generate_quiz"),
        StructuredTool.from_function(save_memory, name="Save_memory"),
        StructuredTool.from_function(retrieve_memory, name="Retrieve_memory"),
        StructuredTool.from_function(summarize_document, name="Summarize_document"),
        StructuredTool.from_function(generate_diagram, name="Generate_diagram"),
    ]


TUTOR_SYSTEM = """You are an AI Tutor with long-term memory tools.

The user message may begin with an [Automatic learner context from saved memory] block — treat it as ground truth about this learner and adapt tone, difficulty, and examples accordingly.

Priorities:
- When the student struggles or says they do not understand, call Save_memory with a line starting WEAKNESS: (topic + one short fact). When they state a goal, use GOAL:. When they master something, use STRENGTH:.
- Still use Retrieve_memory when you need extra detail beyond the injected context.
- Use Save_memory for quiz outcomes, recurring mistakes, and preferences (plain text is fine if no prefix fits).
- Keep explanations concise by default for fast replies; go deeper only if asked.
- Use Generate_quiz for practice; Generate_diagram for processes; Summarize_document only when document text is in the message.

If image or voice context is present, use it directly in your teaching."""


def build_agent_executor(user_id: int) -> AgentExecutor:
    llm = _make_llm()
    tools = build_tools(user_id)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", TUTOR_SYSTEM),
            MessagesPlaceholder("chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ]
    )
    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=False,
        max_iterations=TUTOR_MAX_AGENT_ITERATIONS,
        return_intermediate_steps=False,
        handle_parsing_errors=True,
    )


_executors: dict[int, AgentExecutor] = {}
_exec_lock = threading.Lock()


def get_agent_executor(user_id: int) -> AgentExecutor:
    """One cached AgentExecutor per user (tools bind to that user's FAISS index)."""
    with _exec_lock:
        if user_id not in _executors:
            _executors[user_id] = build_agent_executor(user_id)
        return _executors[user_id]
