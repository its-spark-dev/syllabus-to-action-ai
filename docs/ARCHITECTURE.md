# Syllabus-to-Action AI – Architecture

## Current State
The scheduler is deterministic by default and safe without external services.  
AI refinement is an optional, validated layer layered on top of the planner.

## Core Flow
1. `app.py` collects syllabus text input and generates the initial weekly draft.
2. `parse_syllabi()` structures raw text into normalized events.
3. `generate_weekly_plan()` builds baseline weekly workload and priorities.
4. `generate_plan_with_ai()` applies deterministic refinement and optional IBM WatsonX intelligence.
5. `study_guide` and `weekly_plan` are returned to the UI.

## Weight Logic
- `grading_categories` is preserved as syllabus-authored truth metadata.
- Explicit percentages are surfaced in task labels where available.
- Distributed category weights are used internally for scoring only.

## Determinism Rules
- `anchor_date` is required for repeatability.
- No automatic `date.today()` fallback inside scoring logic.
- Same inputs + same `anchor_date` → stable output.

## AI Layer
- `call_ibm_ai()` is available and guarded by strict schema validation + fallback.
- If AI variables are missing or the model call fails, deterministic output is returned.
