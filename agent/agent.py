from __future__ import annotations

import os
from typing import Any

from anthropic import AsyncAnthropic
from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider

from context import SCHEMA_CONTEXT
from logger import get_logger
from tools.sql.tool import execute_readonly_sql

load_dotenv()

logger = get_logger(__name__)

DEFAULT_MODEL = "google:gemini-2.5-flash"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-6"
DEFAULT_RAKUTEN_GATEWAY_URL = "https://api.ai.public.rakuten-it.com/anthropic/"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "google")

SYSTEM_INSTRUCTIONS = f"""
You are Audit Metric AI, a data analyst for Jira audit and vulnerability tickets.
You can also help the user to give KPI of an individual auditor, such as how many tickets an auditor has resolved, how many tickets an auditor has opened, how many tickets an auditor has closed, etc.

{SCHEMA_CONTEXT}

When answering:
1. Use run_sql to fetch data before answering factual questions.
2. Write SQLite SELECT queries following the SQL rules above.
3. If a query returns an error, fix the SQL and try again.
4. Summarize in plain business language with bullet points.
5. Prefer GROUP BY aggregations; avoid returning huge raw lists.
6. Do not invent numbers — only use query results.
"""

def _build_model() -> str | AnthropicModel:
    if LLM_PROVIDER == "anthropic":
        gateway_key = os.getenv("RAKUTEN_AI_GATEWAY_KEY")
        if not gateway_key:
            raise ValueError("RAKUTEN_AI_GATEWAY_KEY is required when LLM_PROVIDER=anthropic")
        client = AsyncAnthropic(
            base_url=os.getenv("RAKUTEN_API_URL", DEFAULT_RAKUTEN_GATEWAY_URL),
            auth_token=gateway_key,
        )
        model_name = os.getenv("ANTHROPIC_MODEL", DEFAULT_ANTHROPIC_MODEL)
        return AnthropicModel(
            model_name,
            provider=AnthropicProvider(anthropic_client=client),
        )
    return os.getenv("LLM_MODEL", DEFAULT_MODEL)


def _create_audit_agent() -> Agent[None, str]:
    agent = Agent(_build_model(), instructions=SYSTEM_INSTRUCTIONS)

    @agent.tool_plain
    def run_sql(query: str) -> dict[str, Any]:
        """Run a read-only SQL query against the local audit SQLite database."""
        logger.info(f"Agent SQL request: {query}")
        return execute_readonly_sql(query)

    return agent


audit_agent = _create_audit_agent()


def ask(question: str) -> str:
    result = audit_agent.run_sync(question)
    return result.output
