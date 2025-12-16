"""Specification Analysis Agent.

Analyzes user specifications, identifies ambiguities, generates clarifying
questions, and produces structured specification output.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.agents.base import BaseAgent
from app.config import settings
from app.models.estimation import EstimationResult, EstimationRow
from app.models.project import ClarificationQuestion
from app.models.spec import (
    APIEndpoint,
    DataModel,
    Feature,
    StructuredSpec,
    TechRecommendations,
    UIComponent,
)
from app.models.template import SpecTemplate
from app.parsers.csv import parse_csv_spec
from app.parsers.markdown import parse_markdown_spec


class SpecAnalysisInput(BaseModel):
    """Input for specification analysis."""

    spec_format: Literal["markdown", "csv", "text"]
    spec_content: str
    project_name: str
    template: SpecTemplate | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class SpecAnalysisOutput(BaseModel):
    """Output from specification analysis."""

    structured_spec: StructuredSpec
    estimation: EstimationResult | None = None
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
        return """You are a project manager and solution architect.

Your job is to study client requirements, mirror the breakdown style of an existing CSV estimation template, and produce two things:
1) A clear developer-ready structured specification (features, data models, APIs, UI).
2) A task and effort breakdown with hour estimates for each feature/module, staying consistent with the template style when provided.

Input formats:
- Markdown or plain text requests from clients.
- CSV templates that demonstrate how effort is grouped and estimated.

Process:
- Parse the input specification and extract explicit/implicit requirements.
- Use the provided template (when available) as a guide for structure, naming, and effort sizing.
- Identify ambiguities and propose clarifying questions that unblock delivery.
- Produce MoSCoW-prioritized features with acceptance criteria.
- Create an estimation breakdown with realistic hours, QA/PM overhead, and buffer.

Quality standards:
- Every feature has acceptance criteria and clear ownership.
- API endpoints list methods, paths, and request/response essentials.
- Data models define fields and relationships.
- Estimation rows are concrete, actionable tasks a dev team can execute.
"""

    @property
    def tools(self) -> list[str]:
        return ["Read", "Grep", "Glob"]

    @property
    def model(self) -> str:
        return "claude-sonnet-4-5-20250929"

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
        if input_data.spec_format in ("markdown", "text"):
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

        # Rehydrate from final structured spec
        features = structured_spec.features
        data_models = structured_spec.data_models
        api_endpoints = structured_spec.api_endpoints
        ui_components = structured_spec.ui_components
        structured_spec.estimated_complexity = self._estimate_complexity(
            features=features,
            data_models=data_models,
            api_endpoints=api_endpoints,
        )

        # Generate clarification questions based on analysis
        clarification_questions = self._identify_gaps(
            features=features,
            data_models=data_models,
            api_endpoints=api_endpoints,
            ui_components=ui_components,
        )

        estimation = self._build_estimation(
            project_name=input_data.project_name,
            description=structured_spec.description or description,
            features=features,
            complexity=structured_spec.estimated_complexity,
            template=input_data.template,
        )

        if estimation:
            estimation.ensure_csv()

        self.logger.info(
            "spec_analysis.completed",
            features_count=len(features),
            models_count=len(data_models),
            endpoints_count=len(api_endpoints),
            questions_count=len(clarification_questions),
            estimation_total=estimation.grand_total() if estimation else None,
        )

        return SpecAnalysisOutput(
            structured_spec=structured_spec,
            estimation=estimation,
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

    def _build_estimation(
        self,
        project_name: str,
        description: str,
        features: list[Feature],
        complexity: Literal["simple", "medium", "complex"],
        template: SpecTemplate | None = None,
    ) -> EstimationResult | None:
        """Create an estimation breakdown using features and optional template context."""
        base_hours = template.estimated_hours_baseline if template else None
        base_hours = base_hours or 10.0
        base_hours = max(base_hours, 6.0)

        complexity_factor = {
            "simple": 0.9,
            "medium": 1.0,
            "complex": 1.2,
        }[complexity]

        rows: list[EstimationRow] = []
        sequence = 1

        foundation_hours = round(base_hours * 0.65, 1)
        rows.append(
            EstimationRow(
                number=sequence,
                area="Foundation",
                task="Project setup, repository bootstrapping, CI scaffold, environments",
                estimated_hours=foundation_hours,
                notes="Baseline setup influenced by template baseline hours" if template else "Baseline setup",
            )
        )
        sequence += 1

        for feature in features:
            hours = self._estimate_feature_hours(
                feature=feature,
                base_hours=base_hours,
                complexity_factor=complexity_factor,
            )
            rows.append(
                EstimationRow(
                    number=sequence,
                    area=feature.name,
                    task=feature.description or feature.name,
                    estimated_hours=hours,
                    optional=feature.priority in ("could", "wont"),
                    notes="Estimated using template effort style" if template else "Heuristic estimate",
                    feature_id=feature.id,
                )
            )
            sequence += 1

        feature_hours = sum(r.estimated_hours for r in rows if r.area != "Foundation")
        qa_hours = round(max(4.0, feature_hours * 0.18), 1)
        rows.append(
            EstimationRow(
                number=sequence,
                area="Quality",
                task="QA, UAT support, regression passes",
                estimated_hours=qa_hours,
                notes="Includes regression on main user journeys",
            )
        )
        sequence += 1

        deploy_hours = round(max(3.0, feature_hours * 0.1), 1)
        rows.append(
            EstimationRow(
                number=sequence,
                area="Release",
                task="Staging hardening, deployment, smoke tests, handover",
                estimated_hours=deploy_hours,
                notes="Covers staging + production promotion",
            )
        )
        sequence += 1

        total_hours = round(sum(r.estimated_hours for r in rows), 2)
        buffer_hours = round(max(2.0, total_hours * 0.1), 2)

        estimation = EstimationResult(
            template_id=template.id if template else None,
            rows=rows,
            total_hours=total_hours,
            buffer_hours=buffer_hours,
            summary=f"Estimation for {project_name}: {len(features)} feature(s), {complexity} complexity.",
            metadata={
                "base_hours": base_hours,
                "complexity_factor": complexity_factor,
                "template_name": template.name if template else None,
                "description": description,
            },
        )

        return estimation

    def _estimate_feature_hours(
        self,
        feature: Feature,
        base_hours: float,
        complexity_factor: float,
    ) -> float:
        """Estimate hours for a single feature."""
        priority_factor = {
            "must": 1.1,
            "should": 1.0,
            "could": 0.7,
            "wont": 0.4,
        }.get(feature.priority, 1.0)

        risk_keywords = ["payment", "auth", "oauth", "real-time", "export", "analytics"]
        risk_factor = 1.0
        if any(kw in feature.name.lower() or kw in feature.description.lower() for kw in risk_keywords):
            risk_factor += 0.2

        return round(max(2.0, base_hours * priority_factor * complexity_factor * risk_factor), 1)

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

            from app.config import settings
            
            options = ClaudeAgentOptions(
                system_prompt=self.system_prompt,
                permission_mode="plan",  # Read-only mode
                # Pass API key as environment variable for authentication
                env={"ANTHROPIC_API_KEY": settings.anthropic_api_key} if settings.anthropic_api_key else {},
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
