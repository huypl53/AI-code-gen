"""Data models for App-Agent."""

from app.models.deployment import (
    DeploymentInput,
    DeploymentResult,
)
from app.models.generation import (
    CodeGenOptions,
    GeneratedFile,
    GeneratedProject,
)
from app.models.project import (
    ClarificationQuestion,
    PhaseInfo,
    PhaseStatus,
    Project,
    ProjectCreate,
    ProjectOptions,
    ProjectResponse,
    ProjectStatus,
)
from app.models.project_template import (
    ProjectTemplate,
    ProjectTemplateCreate,
    ProjectTemplateResponse,
    TechStack,
    TemplateMatch,
)
from app.models.spec import (
    APIEndpoint,
    ComponentProp,
    DataModel,
    Feature,
    ModelField,
    Relationship,
    StructuredSpec,
    TechRecommendations,
    UIComponent,
)

__all__ = [
    # Project models
    "Project",
    "ProjectCreate",
    "ProjectOptions",
    "ProjectResponse",
    "ProjectStatus",
    "PhaseStatus",
    "PhaseInfo",
    "ClarificationQuestion",
    # Spec models
    "Feature",
    "DataModel",
    "ModelField",
    "Relationship",
    "APIEndpoint",
    "UIComponent",
    "ComponentProp",
    "TechRecommendations",
    "StructuredSpec",
    # Generation models
    "CodeGenOptions",
    "GeneratedFile",
    "GeneratedProject",
    # Deployment models
    "DeploymentInput",
    "DeploymentResult",
    # Project template models
    "ProjectTemplate",
    "ProjectTemplateCreate",
    "ProjectTemplateResponse",
    "TechStack",
    "TemplateMatch",
]
