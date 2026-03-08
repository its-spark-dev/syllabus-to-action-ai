# Design Document

## 1. System Goals

Syllabus-to-Action AI converts unstructured course syllabi into structured, prioritized, and actionable weekly study plans.

The AI layer is an explanation and strategy engine, not the sole planner.

## 2. Core Design Principles

1. Split entrypoints by purpose:
   - `app.py`: core validation and engine entrypoint
   - `dashboard_app.py`: final polished portfolio experience
2. Deterministic baseline behavior
3. Explainable prioritization
4. Modular code structure (`parser`, `planner`, `ai`)
5. Portfolio-friendly deployability

## 3. Architecture Layers

### Layer 1: Extraction

Parse syllabus text into normalized objects:
- assignments
- quizzes
- milestones
- exams
- grading weights and due dates

### Layer 2: Reasoning

Core reasoning in planner layer:
- derive weekly work buckets
- calculate workload stress signals
- prioritize items with guardrails around urgency and weight
- produce study guide summary

Optional AI refinement adds:
- contextual insight text
- strategic recommendations
- scenario simulation interpretation

### Layer 3: Planning

Generate weekly outputs:
- weekly to-do lists
- prioritization rationale
- summary and action guidance

## 4. Module Structure

- `app.py` – Streamlit UI used for core validation and engine verification
- `dashboard_app.py` – final Streamlit UI used as public portfolio deliverable
- `parser/` – syllabus parsing logic
- `planner/` – deterministic planning and scoring
- `ai/` – AI/intelligence connectors and payload shaping
- `data/` – mock syllabi fixtures
- `scripts/` – local utility/testing scripts
- `assets/` – UI visuals

## 5. Deployment Strategy

Designed to run as a lightweight Streamlit app; optional AI calls can be toggled at runtime for portfolio demos.
