# App-Agent Blueprint
Version 0.1.0 · Last updated 2024-12

---

## Snapshot
- AI-driven backend (FastAPI) that turns CSV/Markdown specs into deployed web apps.
- Pipeline: clarify spec → generate code → deploy to Vercel; streamed status over API/SSE.
- Defaults: Next.js 14 + Tailwind, TypeScript, Vitest/Testing Library; deployments via `v0-sdk`.
- Core SDKs: `claude-agent-sdk` (agents), `v0-sdk` (Vercel).

---

## System Flow
1) User POSTs spec → API validates/authenticates.  
2) Orchestrator runs agents sequentially (spec → code → deploy) and tracks phases.  
3) Events stream via SSE; result returns URL + logs.

```
User → FastAPI API → Orchestrator → [SpecAgent → CodingAgent → DevopsAgent] → Vercel
```

---

## Stack
- Runtime: Python 3.11+, FastAPI, asyncio/httpx, Pydantic v2.
- Tooling: uv, ruff, mypy, pytest/pytest-asyncio, pre-commit.
- Infra: Vercel (+ optional Redis/Postgres).

---

## API Surface (v1)
| Endpoint | Purpose | Notes |
| --- | --- | --- |
| `POST /v1/projects` | Create project from spec | body: `name`, `spec_format` (`markdown`|`csv`), `spec_content`, options (`framework`, `styling`, `auto_deploy`, `include_tests`) |
| `GET /v1/projects/{id}` | Project status | returns phase timings, result URL/logs |
| `POST /v1/projects/{id}/clarify` | Submit answers | array of `{question_id, answer}` |
| `GET /v1/projects/{id}/clarifications` | Pending clarifications | questions + metadata |
| `GET /v1/projects/{id}/stream` | SSE stream | events: `phase_started`, `agent_message`, `file_generated`, `deployment_complete` |
| `DELETE /v1/projects/{id}` | Cancel project | best-effort cancellation |

Auth: `Authorization: Bearer <api_key>`.  
Base URLs: prod `https://api.app-agent.dev/v1`, local `http://localhost:8000/v1`.

---

## Agents
**SpecAnalysisAgent**  
- Goal: parse CSV/MD specs, extract features/models/endpoints/UI, raise ambiguities.  
- Output: `StructuredSpec` JSON + clarifications/assumptions.  
- Tools: Read/Write/Grep/Glob; Model: `sonnet`.

**CodingAgent**  
- Goal: generate full project (config, source, tests, docs) with lint-ready output.  
- Defaults: Next.js App Router, Tailwind, TS strict, React Query + Zustand, Zod validation, Vitest.  
- Tools: Read/Write/Edit/Bash/Glob/Grep; Model: `opus`.  
- Output: `GeneratedProject` (files, entrypoint, build/start commands, deps).

**DevopsAgent**  
- Goal: deploy via `v0-sdk`, manage env vars/domains, return URL + logs.  
- Checklist: build script, config file (next/vite), env validation, retries/timeouts.  
- Tools: Read/Bash/Glob (+ v0 tools); Model: `sonnet`.  
- Output: `DeploymentResult` (`success`, `url`, `deployment_id`, `duration_ms`, `logs`/`error`).

---

## Data & Status Models
- ProjectStatus: `pending → analyzing → clarifying → generating → deploying → deployed | failed | cancelled`.
- PhaseStatus: `pending | in_progress | completed | failed | skipped`.
- Project stores: spec format/content/options, phase timings, structured_spec, generated_project, deployment_result, error info.
- StructuredSpec highlights: `features` (with acceptance), `data_models` (fields/relationships), `api_endpoints` (request/response schemas), `ui_components`, `clarifications_needed`, `assumptions`, `tech_recommendations`, `estimated_complexity`.
- GeneratedProject: paths + line counts, entrypoint, build/start commands, deps/dev_deps.

---

## Repo Layout
```
app-agent/
├ app/               # FastAPI app
│ ├ api/             # v1 routers, deps, middleware
│ ├ core/            # orchestrator, session, events, exceptions
│ ├ agents/          # base + spec/coding/devops + registry
│ ├ models/          # project/spec/generation/deployment schemas
│ ├ parsers/         # markdown/csv spec parsers
│ ├ generators/      # Next.js generators + templates
│ └ utils/           # logging, validation, file helpers
├ tests/             # unit + integration + fixtures
├ scripts/           # dev/test/lint helpers
├ .env.example · pyproject.toml · uv.lock · README.md · CLAUDE.md
```

---

## Dev Guidelines
- Type hints everywhere; prefer Pydantic models for I/O and configs.  
- Async-first for I/O; dependency injection via FastAPI deps.  
- Logging: `structlog` JSON by default; include phase + project_id.  
- Errors: custom exceptions per agent; global handler returns `{error, type}` with safe details.  
- File generation order: config → data/models → API → UI → utils → tests → docs.  
- Naming/quality: meaningful identifiers, input validation (Zod on front, Pydantic on back), retries/timeouts for external calls.

---

## Testing
- Pyramid target: 60% unit (models/parsers/utils/agent logic w/ mocked SDK), 30% integration (API + agent orchestration), 10% e2e (pipeline + staged Vercel).  
- Key fixtures: AsyncClient for FastAPI, sample specs (MD/CSV), mocked `claude-agent-sdk`.  
- Commands: `uv run pytest`, `uv run ruff check .`, `uv run mypy app`, `uv run ruff format .`.

---

## Deployment & Ops
- Env (see `.env.example`): `APP_ENV`, `APP_SECRET_KEY`, API host/port/workers, `ANTHROPIC_API_KEY`, `VERCEL_TOKEN`, optional `REDIS_URL`/`DATABASE_URL`, `LOG_LEVEL`, `LOG_FORMAT`.  
- Docker: slim Python base → install uv → `uv sync --frozen` → copy app → run `uvicorn app.main:app`.  
- Compose (dev): `api` with bind mount for hot reload + optional `redis`.  
- CI (GH Actions): checkout → setup Python → install uv → `uv sync` → `ruff check` → `mypy app` → `pytest --cov` → upload coverage.

---

## Security & Guardrails
- Auth: API key required; rate limit (target 100 req/min/key).  
- No sensitive data in logs; redact tokens/keys.  
- Agent safety: restricted tool lists, sandboxed execution, block dangerous shell patterns (`rm -rf /`, `sudo`, `chmod 777`, `curl | bash`).  
- Data handling: specs processed transiently; env vars stay out of repo.  
- Deployment: validate env vars + domains before invoking Vercel; report build failures with log URL.

---

## Quickstart
```bash
uv sync                      # install
uv run uvicorn app.main:app --reload
uv run pytest                # tests
uv run ruff check .          # lint
uv run mypy app              # type check
```
