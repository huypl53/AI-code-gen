"""Unit tests for specification parsers."""

import pytest

from app.parsers.markdown import MarkdownParser, parse_markdown_spec
from app.parsers.csv import CSVParser, parse_csv_spec


class TestMarkdownParser:
    """Tests for MarkdownParser."""

    @pytest.fixture
    def parser(self) -> MarkdownParser:
        return MarkdownParser()

    def test_parse_title(self, parser: MarkdownParser):
        """Test extracting title from markdown."""
        content = "# My Application\n\nSome description"
        result = parser.parse(content)
        assert result.title == "My Application"

    def test_parse_description_section(self, parser: MarkdownParser):
        """Test extracting description section."""
        content = """# App

## Description
This is a test application for managing tasks.

## Features
- Feature 1
"""
        result = parser.parse(content)
        assert "test application" in result.description

    def test_parse_simple_features(self, parser: MarkdownParser):
        """Test parsing simple feature list."""
        content = """# App

## Features
- Create tasks
- Edit tasks
- Delete tasks
"""
        result = parser.parse(content)
        assert len(result.features) == 3
        assert result.features[0].name == "Create tasks"

    def test_parse_bold_features(self, parser: MarkdownParser):
        """Test parsing features with bold names."""
        content = """# App

## Features
- **Create Tasks**: Users can create new tasks
- **Edit Tasks**: Users can modify existing tasks
"""
        result = parser.parse(content)
        assert len(result.features) == 2
        assert result.features[0].name == "Create Tasks"
        assert "create new tasks" in result.features[0].description

    def test_parse_subsection_features(self, parser: MarkdownParser):
        """Test parsing features with subsections."""
        content = """# App

## Features

### Core Features
- User authentication
- Dashboard

### Advanced Features
- Analytics
- Exports
"""
        result = parser.parse(content)
        assert len(result.features) == 4
        # Core features should have higher priority
        core_features = [f for f in result.features if f.priority == "must"]
        assert len(core_features) == 2

    def test_parse_data_model_list(self, parser: MarkdownParser):
        """Test parsing data models from list format."""
        content = """# App

## Data Models

### User
- id: uuid (primary key)
- email: string (required)
- name: string (optional)
"""
        result = parser.parse(content)
        assert len(result.data_models) == 1
        assert result.data_models[0].name == "User"
        assert len(result.data_models[0].fields) == 3

    def test_parse_data_model_table(self, parser: MarkdownParser):
        """Test parsing data models from table format."""
        content = """# App

## Data Models

### Task
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | Yes | Unique identifier |
| title | string | Yes | Task title |
| completed | boolean | No | Completion status |
"""
        result = parser.parse(content)
        assert len(result.data_models) == 1
        assert result.data_models[0].name == "Task"
        assert len(result.data_models[0].fields) == 3
        
        title_field = next(f for f in result.data_models[0].fields if f.name == "title")
        assert title_field.type == "string"
        assert title_field.required is True

    def test_parse_api_endpoints_list(self, parser: MarkdownParser):
        """Test parsing API endpoints from list format."""
        content = """# App

## API Endpoints
- GET /api/tasks - List all tasks
- POST /api/tasks - Create a task
- DELETE /api/tasks/{id} - Delete a task
"""
        result = parser.parse(content)
        assert len(result.api_endpoints) == 3
        
        get_endpoint = next(e for e in result.api_endpoints if e.method == "GET")
        assert get_endpoint.path == "/api/tasks"

    def test_parse_api_endpoints_sections(self, parser: MarkdownParser):
        """Test parsing API endpoints from H3 sections."""
        content = """# App

## API Endpoints

### List Tasks
- **GET** `/api/tasks`
- Returns all tasks

### Create Task
- **POST** `/api/tasks`
- Creates a new task
"""
        result = parser.parse(content)
        assert len(result.api_endpoints) == 2

    def test_parse_ui_components(self, parser: MarkdownParser):
        """Test parsing UI components."""
        content = """# App

## UI Components

### Pages
- Home page with task list
- Settings page

### Components
- TaskList - displays all tasks
- TaskItem - single task row
"""
        result = parser.parse(content)
        assert len(result.ui_components) == 4
        
        pages = [c for c in result.ui_components if c.type == "page"]
        components = [c for c in result.ui_components if c.type == "component"]
        assert len(pages) == 2
        assert len(components) == 2

    def test_parse_full_spec(self, sample_markdown_spec: str):
        """Test parsing a complete specification."""
        result = parse_markdown_spec(sample_markdown_spec)
        
        assert result.title == "Todo Application"
        assert len(result.features) > 0
        assert len(result.data_models) > 0
        assert len(result.api_endpoints) > 0
        assert len(result.ui_components) > 0

    def test_normalize_types(self, parser: MarkdownParser):
        """Test type normalization."""
        assert parser._normalize_type("string") == "string"
        assert parser._normalize_type("VARCHAR") == "string"
        assert parser._normalize_type("int") == "number"
        assert parser._normalize_type("INTEGER") == "number"
        assert parser._normalize_type("bool") == "boolean"
        assert parser._normalize_type("datetime") == "datetime"
        assert parser._normalize_type("timestamp") == "datetime"


class TestCSVParser:
    """Tests for CSVParser."""

    @pytest.fixture
    def parser(self) -> CSVParser:
        return CSVParser()

    def test_parse_basic_csv(self, parser: CSVParser):
        """Test parsing basic CSV with standard columns."""
        content = """feature_name,description,priority
Login,Users can login,must
Dashboard,Main dashboard,should
"""
        result = parser.parse(content)
        assert len(result.features) == 2
        assert result.features[0].name == "Login"
        assert result.features[0].priority == "must"

    def test_parse_csv_with_acceptance_criteria(self, parser: CSVParser):
        """Test parsing CSV with acceptance criteria column."""
        content = """name,description,priority,acceptance_criteria
Login,Users can login,high,"Form shows email and password;Error on invalid credentials;Redirect on success"
"""
        result = parser.parse(content)
        assert len(result.features) == 1
        assert len(result.features[0].acceptance_criteria) == 3

    def test_parse_csv_column_variations(self, parser: CSVParser):
        """Test parsing CSV with varied column names."""
        content = """feature,desc,prio
Create Task,Add new tasks,must
"""
        result = parser.parse(content)
        assert len(result.features) == 1
        assert result.features[0].name == "Create Task"
        assert result.features[0].description == "Add new tasks"

    def test_parse_csv_priority_mapping(self, parser: CSVParser):
        """Test priority value mapping."""
        content = """name,priority
Feature 1,must
Feature 2,high
Feature 3,critical
Feature 4,should
Feature 5,medium
Feature 6,could
Feature 7,low
"""
        result = parser.parse(content)
        
        assert result.features[0].priority == "must"
        assert result.features[1].priority == "must"  # high -> must
        assert result.features[2].priority == "must"  # critical -> must
        assert result.features[3].priority == "should"
        assert result.features[4].priority == "should"  # medium -> should
        assert result.features[5].priority == "could"
        assert result.features[6].priority == "could"  # low -> could

    def test_parse_csv_empty_rows(self, parser: CSVParser):
        """Test handling of rows with empty name."""
        content = """name,description
Feature 1,Description 1
,Empty name row
Feature 2,Description 2
"""
        result = parser.parse(content)
        # Should skip row with empty name
        assert len(result.features) == 2
        assert result.features[0].name == "Feature 1"
        assert result.features[1].name == "Feature 2"

    def test_parse_sample_csv(self, sample_csv_spec: str):
        """Test parsing sample CSV spec."""
        result = parse_csv_spec(sample_csv_spec)
        
        assert len(result.features) > 0
        assert len(result.raw_rows) > 0
        
        # Check for specific features
        feature_names = [f.name for f in result.features]
        assert "User Authentication" in feature_names
        assert "Task Management" in feature_names
