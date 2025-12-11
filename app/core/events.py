"""Event system for Server-Sent Events (SSE)."""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncIterator
from uuid import UUID


@dataclass
class Event:
    """An SSE event."""

    event_type: str
    data: dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_sse(self) -> str:
        """Convert to SSE format."""
        data_json = json.dumps({**self.data, "timestamp": self.timestamp.isoformat()})
        return f"event: {self.event_type}\ndata: {data_json}\n\n"


class EventBus:
    """Simple event bus for project events."""

    def __init__(self):
        self._subscribers: dict[UUID, asyncio.Queue[Event]] = {}

    def subscribe(self, project_id: UUID) -> asyncio.Queue[Event]:
        """Subscribe to events for a project."""
        if project_id not in self._subscribers:
            self._subscribers[project_id] = asyncio.Queue()
        return self._subscribers[project_id]

    def unsubscribe(self, project_id: UUID) -> None:
        """Unsubscribe from project events."""
        self._subscribers.pop(project_id, None)

    async def publish(self, project_id: UUID, event: Event) -> None:
        """Publish an event for a project."""
        if project_id in self._subscribers:
            await self._subscribers[project_id].put(event)

    async def publish_phase_started(self, project_id: UUID, phase: str) -> None:
        """Publish a phase started event."""
        await self.publish(
            project_id,
            Event(event_type="phase_started", data={"phase": phase}),
        )

    async def publish_phase_completed(
        self, project_id: UUID, phase: str, duration_ms: int
    ) -> None:
        """Publish a phase completed event."""
        await self.publish(
            project_id,
            Event(
                event_type="phase_completed",
                data={"phase": phase, "duration_ms": duration_ms},
            ),
        )

    async def publish_agent_message(
        self, project_id: UUID, agent: str, message: str
    ) -> None:
        """Publish an agent message event."""
        await self.publish(
            project_id,
            Event(
                event_type="agent_message",
                data={"agent": agent, "message": message},
            ),
        )

    async def publish_file_generated(
        self, project_id: UUID, path: str, lines: int
    ) -> None:
        """Publish a file generated event."""
        await self.publish(
            project_id,
            Event(
                event_type="file_generated",
                data={"path": path, "lines": lines},
            ),
        )

    async def publish_deployment_complete(self, project_id: UUID, url: str) -> None:
        """Publish a deployment complete event."""
        await self.publish(
            project_id,
            Event(event_type="deployment_complete", data={"url": url}),
        )

    async def publish_error(
        self, project_id: UUID, error: str, phase: str | None = None
    ) -> None:
        """Publish an error event."""
        await self.publish(
            project_id,
            Event(
                event_type="error",
                data={"error": error, "phase": phase},
            ),
        )


# Singleton instance
_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get the event bus singleton."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus
