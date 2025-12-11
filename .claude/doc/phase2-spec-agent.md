# Phase 2: SpecAnalysisAgent - Implementation Notes

## Overview

The SpecAnalysisAgent parses user specifications (Markdown or CSV) and produces structured output for the CodingAgent.

## Components

### MarkdownParser (`app/parsers/markdown.py`)

Parses markdown specifications with support for:
- H1 title extraction
- H2/H3 section splitting
- Feature lists (simple and bold format)
- Data models from list or table format
- API endpoints
- UI components

```python
from app.parsers import parse_markdown_spec

result = parse_markdown_spec(content)
# result.title, result.features, result.data_models, etc.
```

### CSVParser (`app/parsers/csv.py`)

Parses CSV specifications with flexible column mapping:
- `feature_name`, `name`, `title` → Feature name
- `description`, `desc` → Description
- `priority`, `prio` → Priority (must/should/could/wont)
- `acceptance_criteria`, `ac` → Acceptance criteria (semicolon-separated)

### SpecAnalysisAgent (`app/agents/spec_agent.py`)

The main agent that:
1. Parses specs using appropriate parser
2. Identifies gaps and ambiguities
3. Generates clarification questions
4. Estimates project complexity
5. Produces StructuredSpec

**Key Methods:**
- `execute()` - Main entry point
- `_identify_gaps()` - Find missing requirements
- `_estimate_complexity()` - Score project complexity
- `_enhance_with_claude()` - Optional AI enhancement

## Output Schema

```python
class SpecAnalysisOutput:
    structured_spec: StructuredSpec
    clarification_questions: list[ClarificationQuestion]
    needs_clarification: bool
```

## Clarification Questions

Generated when:
- Features lack acceptance criteria
- No data models specified
- Authentication unclear
- No UI components defined

## Tests

28 tests covering:
- Markdown parsing (title, features, models, endpoints, components)
- CSV parsing (columns, priority mapping)
- Agent execution and gap identification
