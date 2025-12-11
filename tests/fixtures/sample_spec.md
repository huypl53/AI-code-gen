# Todo Application

## Description
A modern, responsive todo list application for managing daily tasks. Built with Next.js and Tailwind CSS.

## Features

### Core Features
- **Create Tasks**: Users can create new tasks with a title and optional description
- **Complete Tasks**: Users can mark tasks as complete/incomplete with a checkbox
- **Delete Tasks**: Users can remove tasks they no longer need
- **Edit Tasks**: Users can modify task title and description

### Advanced Features
- **Filter Tasks**: Filter by status (All, Active, Completed)
- **Search Tasks**: Search tasks by title or description
- **Due Dates**: Optional due dates with visual indicators for overdue tasks
- **Priority Levels**: Set task priority (Low, Medium, High)

## Data Models

### Task
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | Yes | Unique identifier |
| title | string | Yes | Task title (max 200 chars) |
| description | string | No | Detailed description |
| completed | boolean | Yes | Completion status (default: false) |
| priority | enum | No | low, medium, high (default: medium) |
| due_date | datetime | No | Optional due date |
| created_at | datetime | Yes | Creation timestamp |
| updated_at | datetime | Yes | Last update timestamp |

## API Endpoints

### Tasks API

#### List Tasks
- **GET** `/api/tasks`
- Query params: `status`, `priority`, `search`, `page`, `limit`
- Returns: Paginated list of tasks

#### Create Task
- **POST** `/api/tasks`
- Body: `{ title, description?, priority?, due_date? }`
- Returns: Created task

#### Get Task
- **GET** `/api/tasks/{id}`
- Returns: Single task

#### Update Task
- **PUT** `/api/tasks/{id}`
- Body: `{ title?, description?, completed?, priority?, due_date? }`
- Returns: Updated task

#### Delete Task
- **DELETE** `/api/tasks/{id}`
- Returns: 204 No Content

## UI Components

### Pages
1. **Home Page** (`/`)
   - Main task list view
   - Filter bar at top
   - Add task button

### Components
1. **TaskList**
   - Displays all tasks
   - Handles empty state
   - Supports infinite scroll

2. **TaskItem**
   - Single task row
   - Checkbox for completion
   - Click to expand/edit
   - Delete button

3. **TaskForm**
   - Create/edit task form
   - Title input (required)
   - Description textarea
   - Priority selector
   - Due date picker

4. **FilterBar**
   - Status filter (All/Active/Completed)
   - Priority filter
   - Search input

5. **Header**
   - App title
   - Task count summary

## Design Requirements

### Colors
- Primary: Blue (#3B82F6)
- Success: Green (#10B981)
- Warning: Yellow (#F59E0B)
- Danger: Red (#EF4444)
- Background: White/Gray

### Typography
- Font: Inter
- Headings: Bold
- Body: Regular

### Responsive
- Mobile-first design
- Breakpoints: sm (640px), md (768px), lg (1024px)
