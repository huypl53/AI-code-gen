"""Pytest configuration and fixtures."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.session import SessionManager, get_session_manager
from app.main import app


@pytest.fixture
def session_manager() -> SessionManager:
    """Create a fresh session manager for tests."""
    return SessionManager()


@pytest.fixture
async def client() -> AsyncClient:
    """Create an async test client with a fresh session manager."""
    # Reset the session manager for each test
    manager = get_session_manager()
    manager._projects.clear()
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    # Cleanup after test
    manager._projects.clear()


@pytest.fixture
def sample_markdown_spec() -> str:
    """Sample markdown specification for testing."""
    return """# Todo Application

## Description
A simple todo list application for managing daily tasks.

## Features
- Create new tasks with title and description
- Mark tasks as complete
- Delete tasks
- Filter tasks by status (all, active, completed)

## Data Models

### Task
- id: uuid (primary key)
- title: string (required, max 200 chars)
- description: string (optional)
- completed: boolean (default: false)
- created_at: datetime
- updated_at: datetime

## API Endpoints

### Tasks
- GET /api/tasks - List all tasks
- POST /api/tasks - Create a new task
- GET /api/tasks/{id} - Get task by ID
- PUT /api/tasks/{id} - Update a task
- DELETE /api/tasks/{id} - Delete a task

## UI Components

### Pages
- Home page with task list
- Task detail modal

### Components
- TaskList - displays all tasks
- TaskItem - single task row
- TaskForm - create/edit task form
- FilterBar - filter tasks by status
"""


@pytest.fixture
def sample_csv_spec() -> str:
    """Sample CSV specification for testing."""
    return """feature_name,description,priority,acceptance_criteria
User Authentication,Users can register and login,must,"User can register with email and password;User can login with credentials;User can logout"
Dashboard,Main dashboard with statistics,should,"Shows total tasks;Shows completed percentage;Shows recent activity"
Task Management,Create and manage tasks,must,"User can create tasks;User can edit tasks;User can delete tasks;User can mark tasks complete"
"""
