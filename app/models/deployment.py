"""Deployment data models."""

from typing import Any, Literal

from pydantic import BaseModel


class DeploymentInput(BaseModel):
    """Input for deployment."""

    project_directory: str
    project_name: str

    environment: Literal["production", "preview"] = "production"
    env_vars: dict[str, str] | None = None

    domain: str | None = None
    team_id: str | None = None


class DeploymentResult(BaseModel):
    """Result of a deployment."""

    success: bool
    url: str = ""
    deployment_id: str = ""

    build_logs_url: str | None = None
    duration_ms: int = 0

    error: str | None = None
    error_details: dict[str, Any] | None = None
