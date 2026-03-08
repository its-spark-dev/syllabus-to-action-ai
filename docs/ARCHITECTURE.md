# Syllabus-to-Action AI – Architecture (Pre-AI)

## Current State
Deterministic scheduling engine only.

## Core Flow
1. `app.py` collects syllabi + weekly draft
2. `generate_plan_with_ai()`
3. `deterministic_ai_refinement()`
4. `study_guide` + `weekly_plan` + `summary` returned

## Weight Logic
- `grading_categories` = official syllabus truth
- explicit item weights shown
- distributed weights used internally only

## Determinism Rules
- `anchor_date` required
- no `date.today()` fallback
- same input → same output

## AI Layer
`call_ibm_ai()` exists but disabled.  
`USE_REAL_AI = False`.
