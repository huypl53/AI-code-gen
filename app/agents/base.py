"""Base agent class for all AI agents."""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Generic, TypeVar

from pydantic import BaseModel

from app.config import settings
from app.utils.logging import get_logger

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class BaseAgent(ABC, Generic[InputT, OutputT]):
    """Base class for AI agents using claude-agent-sdk.
    
    All agents should inherit from this class and implement:
    - name: Agent identifier
    - description: What the agent does
    - system_prompt: Instructions for Claude
    - execute(): Main execution logic
    """

    def __init__(self):
        self.logger = get_logger(f"agent.{self.name}")
        self._validate_config()

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent name/identifier."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this agent does."""
        pass

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """System prompt for Claude."""
        pass

    @property
    def tools(self) -> list[str]:
        """List of tools this agent can use."""
        return ["Read", "Write", "Edit", "Glob", "Grep"]

    @property
    def model(self) -> str:
        """Model to use for this agent."""
        return "sonnet"

    def _validate_config(self) -> None:
        """Validate that required configuration is present."""
        if not settings.anthropic_api_key:
            self.logger.warning(
                "anthropic_api_key not set - agent will fail at runtime"
            )

    @abstractmethod
    async def execute(self, input_data: InputT) -> OutputT:
        """Execute the agent's main task.
        
        Args:
            input_data: Typed input for this agent
            
        Returns:
            Typed output from this agent
        """
        pass

    async def stream_execute(
        self, input_data: InputT
    ) -> AsyncIterator[tuple[str, Any]]:
        """Execute with streaming events.
        
        Yields tuples of (event_type, event_data) during execution.
        """
        # Default implementation just runs execute()
        yield ("started", {"agent": self.name})
        result = await self.execute(input_data)
        yield ("completed", {"agent": self.name, "result": result})
