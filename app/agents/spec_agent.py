"""Specification Analysis Agent.

Analyzes user specifications, identifies ambiguities, generates clarifying
questions, and produces structured specification output.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.agents.base import BaseAgent
from app.config import settings
from app.models.project import ClarificationQuestion
from app.models.spec import (
    APIEndpoint,
    DataModel,
    Feature,
    StructuredSpec,
    TechRecommendations,
    UIComponent,
)
from app.parsers.csv import parse_csv_spec
from app.parsers.markdown import parse_markdown_spec


class SpecAnalysisInput(BaseModel):
    """Input for specification analysis."""

    spec_format: Literal["markdown", "csv"]
    spec_content: str
    project_name: str
    context: dict[str, Any] = Field(default_factory=dict)


class SpecAnalysisOutput(BaseModel):
    """Output from specification analysis."""

    structured_spec: StructuredSpec
    clarification_questions: list[ClarificationQuestion] = Field(default_factory=list)
    needs_clarification: bool = False


class SpecAnalysisAgent(BaseAgent[SpecAnalysisInput, SpecAnalysisOutput]):
    """Agent for analyzing and structuring user specifications.
    
    This agent:
    1. Parses the input specification (Markdown or CSV)
    2. Extracts features, data models, API endpoints, and UI components
    3. Identifies ambiguities and missing information
    4. Generates clarifying questions when needed
    5. Produces a structured specification for the CodingAgent
    """

    @property
    def name(self) -> str:
        return "spec_analysis"

    @property
    def description(self) -> str:
        return (
            "Analyzes user specifications in CSV or Markdown format, "
            "identifies missing requirements, and generates clarifying questions"
        )

    @property
    def system_prompt(self) -> str:
        return """You are a senior software architect specializing in requirements analysis.

Your task is to analyze user specifications and produce a structured output.

## Input Formats
- **Markdown**: Feature lists, user stories, descriptions
- **CSV**: Structured data with columns for features, requirements, etc.

## Analysis Process
1. Parse the input format correctly
2. Extract all explicit requirements
3. Identify implicit requirements
4. Detect ambiguities or missing information
5. Generate clarifying questions if needed
6. Produce structured specification JSON

## Output Format
Always output valid JSON matching the StructuredSpec schema.

## Quality Standards
- Every feature must have acceptance criteria
- API endpoints must have request/response schemas
- Data models must define all fields and relationships
- UI components must specify layout and interactions
"""

    @property
    def tools(self) -> list[str]:
        return ["Read", "Grep", "Glob"]

    @property
    def model(self) -> str:
        return "sonnet"

    async def execute(self, input_data: SpecAnalysisInput) -> SpecAnalysisOutput:
        """Execute specification analysis.
        
        This implementation uses a hybrid approach:
        1. First, parse the spec using our parsers
        2. Then, optionally use Claude to enhance the analysis
        """
        self.logger.info(
            "spec_analysis.started",
            format=input_data.spec_format,
            content_length=len(input_data.spec_content),
        )

        # Parse the specification
        if input_data.spec_format == "markdown":
            parsed = parse_markdown_spec(input_data.spec_content)
            features = parsed.features
            data_models = parsed.data_models
            api_endpoints = parsed.api_endpoints
            ui_components = parsed.ui_components
            description = parsed.description or f"{input_data.project_name} application"
        else:
            parsed = parse_csv_spec(input_data.spec_content)
            features = parsed.features
            data_models = []
            api_endpoints = []
            ui_components = []
            description = f"{input_data.project_name} application"

        # Generate clarification questions based on analysis
        clarification_questions = self._identify_gaps(
            features=features,
            data_models=data_models,
            api_endpoints=api_endpoints,
            ui_components=ui_components,
        )

        # Determine complexity
        complexity = self._estimate_complexity(
            features=features,
            data_models=data_models,
            api_endpoints=api_endpoints,
        )

        # Build structured spec
        structured_spec = StructuredSpec(
            project_name=input_data.project_name,
            description=description,
            features=features,
            data_models=data_models,
            api_endpoints=api_endpoints,
            ui_components=ui_components,
            tech_recommendations=TechRecommendations(
                framework="nextjs",
                styling="tailwind",
                state_management="zustand",
                rationale="Modern React stack with excellent DX and performance",
            ),
            estimated_complexity=complexity,
        )

        # Check if we need Claude to enhance the analysis
        if settings.anthropic_api_key and self._should_enhance_with_ai(structured_spec):
            enhanced = await self._enhance_with_claude(input_data, structured_spec)
            if enhanced:
                structured_spec = enhanced

        self.logger.info(
            "spec_analysis.completed",
            features_count=len(features),
            models_count=len(data_models),
            endpoints_count=len(api_endpoints),
            questions_count=len(clarification_questions),
        )

        return SpecAnalysisOutput(
            structured_spec=structured_spec,
            clarification_questions=clarification_questions,
            needs_clarification=len(clarification_questions) > 0,
        )

    def _identify_gaps(
        self,
        features: list[Feature],
        data_models: list[DataModel],
        api_endpoints: list[APIEndpoint],
        ui_components: list[UIComponent],
    ) -> list[ClarificationQuestion]:
        """Identify gaps in the specification that need clarification."""
        questions: list[ClarificationQuestion] = []

        # Check for missing acceptance criteria
        features_without_ac = [f for f in features if not f.acceptance_criteria]
        if features_without_ac:
            questions.append(
                ClarificationQuestion(
                    category="feature",
                    question=f"The following features lack acceptance criteria: {', '.join(f.name for f in features_without_ac[:3])}. Can you provide specific acceptance criteria for these?",
                    required=False,
                    context="Acceptance criteria help ensure features are implemented correctly",
                )
            )

        # Check for missing data models if we have features
        if features and not data_models:
            questions.append(
                ClarificationQuestion(
                    category="technical",
                    question="No data models were specified. What data entities does this application need? (e.g., User, Task, etc.)",
                    required=True,
                    context="Data models are essential for generating database schemas and API types",
                )
            )

        # Check for authentication
        auth_keywords = ["auth", "login", "register", "user", "account"]
        has_auth_features = any(
            any(kw in f.name.lower() or kw in f.description.lower() for kw in auth_keywords)
            for f in features
        )
        if not has_auth_features and features:
            questions.append(
                ClarificationQuestion(
                    category="feature",
                    question="Does this application require user authentication?",
                    options=["Yes, with email/password", "Yes, with social login", "No authentication needed"],
                    required=True,
                    context="Authentication affects many aspects of the application architecture",
                )
            )

        # Check for UI if we have features but no components
        if features and not ui_components:
            questions.append(
                ClarificationQuestion(
                    category="design",
                    question="What kind of user interface is needed?",
                    options=["Web application (browser)", "Mobile-responsive web app", "Admin dashboard"],
                    required=True,
                    context="UI type affects component library choices and responsive design",
                )
            )

        return questions

    def _estimate_complexity(
        self,
        features: list[Feature],
        data_models: list[DataModel],
        api_endpoints: list[APIEndpoint],
    ) -> Literal["simple", "medium", "complex"]:
        """Estimate project complexity based on specification."""
        # Simple scoring
        score = 0

        # Feature count
        if len(features) > 10:
            score += 3
        elif len(features) > 5:
            score += 2
        else:
            score += 1

        # Data model complexity
        if len(data_models) > 5:
            score += 3
        elif len(data_models) > 2:
            score += 2
        else:
            score += 1

        # API endpoint count
        if len(api_endpoints) > 15:
            score += 3
        elif len(api_endpoints) > 5:
            score += 2
        else:
            score += 1

        # Check for complex features
        complex_keywords = ["real-time", "sync", "payment", "oauth", "websocket", "notification"]
        for feature in features:
            if any(kw in feature.name.lower() or kw in feature.description.lower() for kw in complex_keywords):
                score += 1

        if score >= 8:
            return "complex"
        elif score >= 5:
            return "medium"
        else:
            return "simple"

    def _should_enhance_with_ai(self, spec: StructuredSpec) -> bool:
        """Determine if we should use Claude to enhance the analysis."""
        # Enhance if we have limited structured data
        return (
            len(spec.features) < 3
            or len(spec.data_models) == 0
            or len(spec.api_endpoints) == 0
        )

    def _normalize_ai_features(self, features_data: list[dict]) -> list[dict]:
        """Normalize AI-generated features to match our schema."""
        priority_mapping = {
            "high": "must",
            "critical": "must",
            "essential": "must",
            "medium": "should",
            "normal": "should",
            "low": "could",
            "optional": "could",
            "nice-to-have": "could",
            "future": "wont",
            "later": "wont",
        }
        
        normalized = []
        for i, feature in enumerate(features_data):
            # Ensure id exists
            if "id" not in feature or not feature["id"]:
                name = feature.get("name", f"feature_{i}")
                # Create id from name: "Task Management" -> "task_management"
                feature["id"] = name.lower().replace(" ", "_").replace("-", "_")
            
            # Normalize priority
            if "priority" in feature:
                priority = str(feature["priority"]).lower()
                if priority in priority_mapping:
                    feature["priority"] = priority_mapping[priority]
                elif priority not in ["must", "should", "could", "wont"]:
                    feature["priority"] = "should"  # Default to "should"
            
            normalized.append(feature)
        
        return normalized

    async def _enhance_with_claude(
        self,
        input_data: SpecAnalysisInput,
        base_spec: StructuredSpec,
    ) -> StructuredSpec | None:
        """Use Claude to enhance the specification analysis."""
        try:
            from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, AssistantMessage, TextBlock
            import json

            self.logger.info("spec_analysis.enhancing_with_ai")

            options = ClaudeAgentOptions(
                system_prompt=self.system_prompt,
                permission_mode="plan",  # Read-only mode
            )

            prompt = f"""Analyze this specification and enhance the structured output.

## Current Parsed Spec
```json
{base_spec.model_dump_json(indent=2)}
```

## Original Specification
```{input_data.spec_format}
{input_data.spec_content}
```

Please analyze the original specification and:
1. Add any missing features
2. Infer data models from the features if not specified
3. Suggest API endpoints based on data models
4. Identify UI components needed

## CRITICAL: Feature Schema Requirements
Each feature MUST have:
- "id": A unique snake_case identifier (e.g., "task_management", "user_auth")
- "name": Human-readable name
- "description": Feature description
- "priority": MUST be one of: "must", "should", "could", "wont" (MoSCoW method)
  - Use "must" for essential features
  - Use "should" for important but not critical
  - Use "could" for nice-to-have features
  - Use "wont" for future/deferred features

Respond with ONLY a valid JSON object matching the StructuredSpec schema.
"""

            async with ClaudeSDKClient(options=options) as client:
                await client.query(prompt)

                response_text = ""
                async for message in client.receive_response():
                    if isinstance(message, AssistantMessage):
                        for block in message.content:
                            if isinstance(block, TextBlock):
                                response_text += block.text

                # Try to parse JSON from response
                if response_text:
                    # Extract JSON from response (may be wrapped in markdown)
                    json_match = response_text
                    if "```json" in response_text:
                        start = response_text.find("```json") + 7
                        end = response_text.find("```", start)
                        json_match = response_text[start:end]
                    elif "```" in response_text:
                        start = response_text.find("```") + 3
                        end = response_text.find("```", start)
                        json_match = response_text[start:end]

                    try:
                        enhanced_data = json.loads(json_match.strip())
                        
                        # Normalize features to match our schema
                        if "features" in enhanced_data and enhanced_data["features"]:
                            enhanced_data["features"] = self._normalize_ai_features(
                                enhanced_data["features"]
                            )
                        
                        return StructuredSpec(**enhanced_data)
                    except (json.JSONDecodeError, ValueError) as e:
                        self.logger.warning(
                            "spec_analysis.ai_enhancement_parse_failed",
                            error=str(e),
                        )

        except ImportError:
            self.logger.warning("claude-agent-sdk not available")
        except Exception as e:
            self.logger.warning(
                "spec_analysis.ai_enhancement_failed",
                error=str(e),
            )

        return None
