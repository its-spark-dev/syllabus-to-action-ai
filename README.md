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

- The planning engine currently runs fully deterministic without external AI calls.
- `anchor_date` is required to keep scheduling stable and reproducible across runs.
- Official `grading_categories` are preserved exactly when present.
- Distributed category weights are used internally for scoring only.
- No artificial/distributed weights are displayed in the UI.
- Summary and risk analysis calculations are driven by the same `anchor_date`.

Architecture overview:
`app.py` → `generate_plan_with_ai()` → `deterministic_ai_refinement()`

Current runtime mode:
- `USE_REAL_AI = False` (default)
- AI integration layer is present but not yet active in default execution.

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
