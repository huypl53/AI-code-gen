"""Agent registry for managing available agents."""

from functools import lru_cache
from typing import Any

from app.agents.base import BaseAgent
from app.utils.logging import get_logger

logger = get_logger(__name__)


class AgentRegistry:
    """Registry for managing AI agents."""

    def __init__(self):
        self._agents: dict[str, type[BaseAgent[Any, Any]]] = {}

    def register(self, agent_class: type[BaseAgent[Any, Any]]) -> None:
        """Register an agent class."""
        # Create temporary instance to get name
        instance = agent_class()
        name = instance.name

        if name in self._agents:
            logger.warning(f"Overwriting existing agent: {name}")

        self._agents[name] = agent_class
        logger.info(f"Registered agent: {name}")

    def get(self, name: str) -> type[BaseAgent[Any, Any]] | None:
        """Get an agent class by name."""
        return self._agents.get(name)

    def create(self, name: str) -> BaseAgent[Any, Any] | None:
        """Create an agent instance by name."""
        agent_class = self.get(name)
        if agent_class:
            return agent_class()
        return None

    def list_agents(self) -> list[str]:
        """List all registered agent names."""
        return list(self._agents.keys())


# Singleton instance
_registry: AgentRegistry | None = None


@lru_cache
def get_agent_registry() -> AgentRegistry:
    """Get the agent registry singleton."""
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry
