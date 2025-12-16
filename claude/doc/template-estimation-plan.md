Plan for template-driven estimation update

Goals
- Store uploaded CSV files as reusable spec templates.
- Make the spec agent act like a project manager: break down features, propose per-feature effort estimates, and produce developer-ready specs.
- When a client submits markdown/text requirements, reuse the stored template to (a) return an estimation CSV for the new project and (b) continue generating the demo app.

Steps
- Template storage & API: Introduce an in-memory template manager/model, plus REST endpoints to create/list/get/set-default templates for uploaded CSV files.
- Data model updates: Extend project/spec models with template references and an estimation structure (rows + totals + CSV rendering) so we can persist and expose the calculations.
- Spec agent changes: Update the system prompt and execution flow to consume an optional base template, generate a task breakdown with estimates, and emit both structured spec and estimation CSV.
- Pipeline & API wiring: Pass the chosen/default template into spec analysis, store estimation outputs on the project, and surface them in project API responses without breaking codegen/deployment flow.
- Tests: Cover template manager and APIs, spec agent estimation shape, and updated project/orchestrator behavior.
