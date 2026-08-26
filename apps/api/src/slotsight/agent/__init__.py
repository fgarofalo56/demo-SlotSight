"""Conversational layer.

A presentation shell over ``slotsight.analytics``. It selects which
deterministic function to run and phrases the result; it never computes a
figure and never queries the database directly.

    tools.py          what the model is allowed to call, and the dispatch
    azure_openai.py   client construction - Entra auth, no API keys
    orchestrator.py   the tool-calling loop and the system prompt
"""

from slotsight.agent import azure_openai, orchestrator, tools

__all__ = ["azure_openai", "orchestrator", "tools"]
