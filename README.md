![CI](https://github.com/your-org/syllabus-to-action-ai/actions/workflows/ci.yml/badge.svg)

# Syllabus-to-Action AI

AI-powered hackathon project that turns unstructured course syllabi into prioritized, actionable weekly study plans.

> **Project type:** Portfolio demo + prototype (hackathon-ready, production-friendly architecture)

## Hackathon context
This project was built as a rapid-response demo focused on one pain point students repeatedly face: taking detailed syllabi and turning them into a weekly execution plan.

The baseline app (`app.py`) remains stable and deterministic, with optional AI refinement via IBM WatsonX when credentials are configured.

## What it does
- Converts multiple syllabi into structured tasks (assignments, quizzes, milestones, exams)
- Generates weekly workload-aware to-do lists
- Prioritizes by urgency + grading weight + risk
- Produces a course-level study guide summary
- Explains why high-stress periods are risky
- Keeps core planning deterministic even when AI is unavailable

## Tech stack
- **Python 3.10+**
- **Streamlit** for web UI
- **IBM WatsonX + Granite** (optional AI refinement path)
- **Regex / parser rules + scheduling engine** in `parser/` and `planner/`

## Repository structure
```
syllabus-to-action-ai/
├── app.py                     # Primary portfolio entrypoint (Streamlit)
├── dashboard_app.py           # Optional premium dashboard UI variant
├── requirements.txt           # Python dependencies
├── .env.example              # Optional WatsonX credentials template
├── .github/                  # GitHub workflows and templates
│   └── workflows/
│       └── ci.yml            # Compile + smoke checks
├── Makefile                  # Quick developer commands
├── LICENSE                   # MIT
├── ai/                       # AI + planning engine glue
├── parser/                   # Syllabus parsing logic
├── planner/                  # Deterministic weekly planner
├── data/                     # Mock sample syllabi used for manual testing
├── assets/                   # UI assets (themes, background visuals)
├── scripts/                  # Utility/test scripts
├── docs/                     # Project documentation
│   ├── ARCHITECTURE.md
│   ├── DESIGN.md
│   ├── INSTALL.md
│   ├── USAGE.md
│   ├── CONTRIBUTING.md
│   ├── RELEASE_NOTES.md
│   ├── CHANGELOG.md
│   └── screenshots/
└── .gitignore
```

## Quick start
### 1) Install dependencies
```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
python -m pip install -r requirements.txt
```

### 2) Run the app
```bash
streamlit run app.py
```

Optional: run the premium UI
```bash
streamlit run dashboard_app.py
```

You can also use Makefile shortcuts:
```bash
make setup      # install dependencies
make run        # run app.py
make run-dashboard # run dashboard_app.py
make verify     # compile + import smoke checks
```

### 3) (Optional) enable AI refinement
1. Set `WATSONX_API_KEY` and `WATSONX_URL` environment variables
2. (Optional but recommended) set `WATSONX_PROJECT_ID`
3. In the app, toggle **Use IBM AI for refinement**
4. Keep default deterministic mode if you want reproducible results without external dependencies

## Example usage
1. Open the app and choose the number of courses.
2. Paste each syllabus into the text area.
3. Click **Generate Plan**.
4. Review:
   - `Weekly To-Do Lists`
   - `Study Guide`
   - summary cards (focus tasks + upcoming high-stakes assessments)

You can also use the included sample button in the UI to quickly load mock syllabi and verify the plan output end-to-end.

## Public project checklist
- [x] Clean structure and clear entrypoint (`app.py`)
- [x] Reproducible setup (`requirements.txt`, `Makefile`, `.env.example`)
- [x] Documentation consolidated under `docs/`
- [x] CI guardrails (`.github/workflows/ci.yml`)
- [x] Open-source license (`LICENSE`)

## Screenshots
### UI snapshots

Below is a visual reference of the current app theming.

![Syllabus-to-Action AI visual style](assets/wallpaper.svg)

To add real UI screenshots, place them in `docs/screenshots/`:
- `docs/screenshots/app-home.png`
- `docs/screenshots/dashboard-home.png`

## API / behavior notes
- Core planning is deterministic by default for stable results.
- AI refinement is additive and guarded behind a strict validation + fallback path.
- The planner output contracts are defined by module boundaries in `parser/`, `planner/`, and `ai/`.

## Developer experience improvements
- Primary documentation now lives in one place: `docs/`
- Entry point is explicit (`app.py`)
- Optional helper script is separated into `scripts/`
- Lightweight structure makes onboarding new contributors easy

## Contributing
See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)

## Security
See [SECURITY.md](SECURITY.md) for responsible vulnerability reporting.
