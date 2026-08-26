"""HTTP routers.

One router per resource. Every router depends on ``slotsight.analytics`` for
its numbers and never issues its own ad-hoc SQL, so the REST API, the MCP
server, and the chat agent cannot drift into disagreeing about the same
question.
"""

from slotsight.routers import chat, floor, health, machines, market, recommendations

__all__ = ["chat", "floor", "health", "machines", "market", "recommendations"]
