# Changelog

## [Unreleased]
- Hardened AI KPI calculation to use real `weekly_metrics` values:
  - `acceleration_index` now derives from max `stress_acceleration_percent` across weeks.
  - `compression_risk` now derives from peak-week `compression_weight_percent` × `compression_window_days` (normalized/capped).
  - Added warning log when `peak_week` is missing from `weekly_metrics` and fallback week selection is applied.
- Expanded AI output schema stability and determinism:
  - Added `peak_delta_percent` to KPI block (baseline vs scenario).
  - Enforced strict validation for KPI and narrative contracts.
  - Added deterministic post-parse override to keep critical KPI fields aligned with engine metrics.
- Upgraded simulation intelligence narrative:
  - Narrative now explicitly reports peak change, week shift, acceleration change, and compression change.
  - Scenario selection is deterministic (`active_scenario` precedence, then best peak reduction).
- Strengthened `why_risky` root-cause explanation:
  - Uses structured peak-week metrics (`exam_count`, `milestone_count`, `weekly_weight_sum`, `compression_weight_percent`, `compression_window_days`, `stress_acceleration_percent`).
  - Detail text now references KPI values directly (`peak_stress_score`, `volatility_index`, `risk_week_ratio`, `burnout_probability_percent`, `peak_delta_percent`).
- Improved time allocation strategy:
  - Allocation now bases on total exam weight across courses, compression presence, and upcoming exam weight, normalized to 100%.
- Added/updated engine-side integration checks in `ai/test_ai.py`:
  - Validates expanded KPI fields.
  - Validates simulation narrative contract tokens.
- Added `dashboard_app.py` as a dedicated premium SaaS dashboard UI while preserving existing engine/business outputs (`weekly_plan`, `study_guide`, `weekly_metrics`).
- Integrated Plotly-based analytics visuals (weekly workload intelligence line chart and per-course grading donut chart) with dark glass styling and responsive rendering.
- Upgraded chart intelligence UX: peak-week overload highlighting, sustainable threshold detection, stress-acceleration signals, and AI-oriented annotations/tooltips.
- Added dynamic grading-impact visualization controls with course switching and center-weight labels for faster comparative course analysis.
- Added `plotly` to project dependencies in `requirements.txt`.
- Pre-AI stabilization freeze completed: deterministic-only execution path documented and consolidated for a clean baseline snapshot.
- Deterministic anchor-date contract enforced: `generate_plan_with_ai` now requires `anchor_date` to eliminate runtime date drift and ensure stable scheduling behavior.
- UI-facing weight display contract tightened: only explicit assessment weights are shown in tasks/upcoming items; distributed/internal weights remain scoring-only and `None%` display is removed.
- Category-based weight distribution instead of naive equal split: distributes grading-category weight across unweighted matching items to avoid inflating single tasks; implemented via category matching and per-item allocation in deterministic scoring.
- Effective weight logic for priority scoring: uses explicit task weight when present, otherwise uses distributed category weight to compute priority; prevents over- or under-weighting tasks without explicit percentages.
- Exam guard mechanism for high-weight exams within 14 days: ensures upcoming high-weight exams sort ahead of low-value work, keeping critical assessments at the top of weekly priorities.
- Weekly weight accumulation using per-task effective weights: weekly weight totals now sum per-task effective weights rather than collapsing categories, improving weekly load fidelity.
- Weekly stress and risk metrics added: calculates weekly stress score and risk level based on minutes/weights to surface heavy weeks; stored in study guide metadata.
- Improved duplicate detection and normalization: normalizes task titles and deduplicates by course/title/due to prevent repeated entries from skewing priorities.
- Prep scoring capped below real assessments: prep tasks are constrained to score below their corresponding assessment to avoid overtaking the actual due item.
- Improved weekly and end-term risk analysis: adds collision and end-term workload warnings using weekly weights and exam counts for better risk signaling.
- Refined sorting using exam_guard and priority_score: deterministic sorting prioritizes guarded exams, then priority score, then due date for stable, explainable ordering.

## [0.1.0] – Initial release
- Baseline deterministic engine generated weekly plans from parsed tasks with simple keyword heuristics, basic date bucketing, and static priority labels.
