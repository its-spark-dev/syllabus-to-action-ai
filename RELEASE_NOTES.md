## [Unreleased]
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

## v1.1.0 – AI Integration & Engine Stabilization
- Watsonx connected and tested
- Deterministic scheduling stabilized
- Weight-aware priority working
- Weekly risk analysis added
- Parser robustness improved
- Known issue: total weight may exceed 100% if participation included