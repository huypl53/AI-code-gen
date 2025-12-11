# Phase 3: CodingAgent - Implementation Notes

## Overview

The CodingAgent generates complete Next.js applications from structured specifications.

## Components

### CodingAgent (`app/agents/coding_agent.py`)

Main agent that:
1. Takes StructuredSpec as input
2. Creates project structure
3. Generates all source files
4. Returns GeneratedProject

**Two Modes:**
1. **Template Mode** (default) - Uses NextJSProjectGenerator
2. **Claude Mode** - Uses claude-agent-sdk for AI generation (when API key available)

### NextJSProjectGenerator (`app/generators/nextjs/project.py`)

Template-based generator that creates:

| File | Description |
|------|-------------|
| `package.json` | Dependencies and scripts |
| `tsconfig.json` | TypeScript configuration |
| `tailwind.config.ts` | Tailwind CSS configuration |
| `next.config.js` | Next.js configuration |
| `src/app/layout.tsx` | Root layout |
| `src/app/page.tsx` | Home page |
| `src/app/globals.css` | Global styles |
| `src/types/index.ts` | TypeScript types from data models |
| `src/app/api/*/route.ts` | API routes |
| `src/components/*.tsx` | UI components |
| `README.md` | Project documentation |

## Generated Components

Base components always included:
- `Button` - Variant support (primary, secondary, danger)
- `Input` - With label and error states
- `Card` - Container with optional title
- `Header` - Application header

## Type Generation

Converts data models to TypeScript:

```typescript
// From DataModel with fields
export interface Task {
  id: string;      // uuid -> string
  title: string;   // string -> string
  completed: boolean;
  created_at: Date; // datetime -> Date
}
```

## API Route Generation

Creates Next.js App Router API routes:

```typescript
// src/app/api/tasks/route.ts
export async function GET(request: Request) {
  // ...
}

export async function POST(request: Request) {
  // ...
}
```

## Tests

10 tests covering:
- File generation
- Type conversion
- API route creation
- Component generation
- File system writes
