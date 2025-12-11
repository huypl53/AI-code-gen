"""Specification data models."""

from typing import Literal

from pydantic import BaseModel, Field


class Feature(BaseModel):
    """A feature in the specification."""

    id: str
    name: str
    description: str
    priority: Literal["must", "should", "could", "wont"] = "should"

    user_stories: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)

    dependencies: list[str] = Field(default_factory=list)
    estimated_effort: Literal["small", "medium", "large"] | None = None


class ModelField(BaseModel):
    """A field in a data model."""

    name: str
    type: str  # "string", "number", "boolean", "date", "json", etc.
    required: bool = True
    default: str | None = None
    validation: str | None = None  # e.g., "email", "url", "min:1|max:100"
    description: str | None = None


class Relationship(BaseModel):
    """A relationship between data models."""

    type: Literal["one_to_one", "one_to_many", "many_to_many"]
    target_model: str
    field_name: str
    inverse_field: str | None = None


class DataModel(BaseModel):
    """A data model / entity in the specification."""

    name: str
    description: str

    fields: list[ModelField] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)

    indexes: list[str] = Field(default_factory=list)
    unique_constraints: list[list[str]] = Field(default_factory=list)


class APIEndpoint(BaseModel):
    """An API endpoint specification."""

    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    path: str
    description: str

    auth_required: bool = True
    rate_limit: str | None = None

    request_body: dict | None = None  # JSON Schema
    query_params: dict | None = None
    path_params: list[str] | None = None

    response_schema: dict = Field(default_factory=dict)
    error_responses: dict[int, str] = Field(default_factory=dict)


class ComponentProp(BaseModel):
    """A prop for a UI component."""

    name: str
    type: str
    required: bool = True
    default: str | None = None
    description: str | None = None


class UIComponent(BaseModel):
    """A UI component specification."""

    name: str
    type: Literal["page", "layout", "component", "modal", "form"]
    description: str

    route: str | None = None  # For pages
    props: list[ComponentProp] = Field(default_factory=list)

    children: list[str] = Field(default_factory=list)
    state_requirements: list[str] = Field(default_factory=list)
    api_dependencies: list[str] = Field(default_factory=list)


class TechRecommendations(BaseModel):
    """Technology recommendations for the project."""

    framework: str = "nextjs"
    styling: str = "tailwind"
    state_management: str = "zustand"
    database: str | None = None
    auth_provider: str | None = None

    additional_libraries: list[str] = Field(default_factory=list)
    rationale: str = ""


class StructuredSpec(BaseModel):
    """Complete structured specification output from SpecAnalysisAgent."""

    project_name: str
    description: str

    features: list[Feature] = Field(default_factory=list)
    data_models: list[DataModel] = Field(default_factory=list)
    api_endpoints: list[APIEndpoint] = Field(default_factory=list)
    ui_components: list[UIComponent] = Field(default_factory=list)

    assumptions: list[str] = Field(default_factory=list)

    tech_recommendations: TechRecommendations = Field(
        default_factory=TechRecommendations
    )
    estimated_complexity: Literal["simple", "medium", "complex"] = "medium"
