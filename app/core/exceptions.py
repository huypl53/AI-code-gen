"""Custom exceptions for App-Agent."""

from typing import Any


class AppAgentError(Exception):
    """Base exception for App-Agent."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class ValidationError(AppAgentError):
    """Validation error."""

    pass


class ProjectNotFoundError(AppAgentError):
    """Project not found."""

    def __init__(self, project_id: str):
        super().__init__(
            f"Project not found: {project_id}",
            {"project_id": project_id},
        )


class SpecParsingError(AppAgentError):
    """Failed to parse specification."""

    def __init__(self, message: str, line: int | None = None):
        details = {}
        if line is not None:
            details["line"] = line
        super().__init__(f"Spec parsing error: {message}", details)


class AgentExecutionError(AppAgentError):
    """Agent failed during execution."""

    def __init__(self, agent: str, phase: str, message: str):
        super().__init__(
            f"Agent '{agent}' failed in phase '{phase}': {message}",
            {"agent": agent, "phase": phase},
        )
        self.agent = agent
        self.phase = phase


class DeploymentError(AppAgentError):
    """Deployment to Vercel failed."""

    def __init__(self, message: str, build_logs: str | None = None):
        details = {}
        if build_logs:
            details["build_logs"] = build_logs
        super().__init__(f"Deployment failed: {message}", details)
