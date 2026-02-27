# Syllabus-to-Action AI

An AI-powered web application that converts multiple course syllabi into prioritized weekly to-do lists and study guides.

## 🚀 Overview

Students often receive detailed syllabi at the beginning of a semester but struggle to translate that information into actionable weekly execution plans.

This project transforms static syllabi into dynamic, time-aware weekly to-do lists and structured study guides.

Powered by IBM WatsonX and Granite models.

---

## 🎯 Problem

Students do not struggle due to lack of information.  
They struggle due to lack of structured execution.

Syllabi contain deadlines, exams, grading weights, and project milestones, but students must manually organize and prioritize these tasks.

---

## 💡 Solution

Syllabus-to-Action AI:

- Extracts assignments, exams, and deadlines
- Analyzes workload and assessment weight
- Generates prioritized weekly to-do lists
- Produces contextual study guides
- Explains why tasks are prioritized

---

## 🏗 Architecture

User Input (Syllabi)
→ Parsing Layer
→ Reasoning Engine (IBM WatsonX + Granite)
→ Weekly Plan Generator
→ To-Do List + Study Guide Output

---

## Deterministic Engine (Pre-AI State)

- The planning core remains deterministic and reproducible.
- `anchor_date` is required to keep scheduling stable across runs.
- Official `grading_categories` are preserved exactly when present.
- Distributed category weights are used internally for scoring only.
- No artificial/distributed weights are displayed in UI task labels.
- Weekly risk/stress metrics are computed deterministically and exposed to the AI intelligence layer.

Architecture overview:
`app.py` → `generate_plan_with_ai()` → `deterministic_ai_refinement()`

Current runtime mode:
- `USE_REAL_AI = False` (default)
- IBM watsonx integration is available (`granite-4-h-small`) and guarded by deterministic fallback logic.

---

## AI Intelligence Layer (Current)

- Single-request AI contract with strict JSON schema validation.
- Deterministic fallback is always available when parsing/model calls fail.
- KPI block includes:
  - `peak_stress_score`
  - `volatility_index`
  - `risk_week_ratio`
  - `burnout_probability_percent`
  - `acceleration_index`
  - `compression_risk`
  - `peak_delta_percent`
- `why_risky` includes structured peak-week root-cause metrics:
  - `exam_count`, `milestone_count`, `weekly_weight_sum`
  - `compression_weight_percent`, `compression_window_days`
  - `stress_acceleration_percent`
- Simulation intelligence includes:
  - deterministic scenario selection
  - `simulation_impact` with peak delta + week-shift signal
  - narrative reporting peak/shift/acceleration/compression changes
- Time allocation strategy is derived from:
  - total exam weight across courses
  - compression presence
  - nearest upcoming exam weight
  - normalized to 100%.

---

## Dashboards

- `app.py`: baseline Streamlit interface.
- `dashboard_app.py`: premium SaaS-style dashboard (glass dark theme + Plotly intelligence charts) using the same backend outputs without changing engine behavior.

---

## Quick Validation

Run AI layer integration check with mock syllabi:

```bash
python3 ai/test_ai.py
```

---

## 🔮 Future Improvements

- Canvas LMS integration
- Real-time assignment sync
- Personalized study time adjustments
- Workload overload detection
- Calendar export support

---

## 🧠 Tech Stack

- Python
- Streamlit
- IBM WatsonX
- Granite LLM
- IBM Cloud (deployment ready)

---

## 📦 Status

MVP under active development.
IBM AI integration completed during hackathon phase.
