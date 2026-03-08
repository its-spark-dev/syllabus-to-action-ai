# Installation Guide

## Requirements

- Python 3.10+  
- `pip` or `python -m pip`

## Quick setup

```bash
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
# Windows:
# .venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Development shortcuts

- `make setup`: install dependencies
- `make run`: run `app.py` (engine validation shell)
- `make run-dashboard`: run `dashboard_app.py`
- `make verify`: compile + import smoke checks (also used by CI)

## Demo assets

The demo video is hosted on Google Drive, so no large local media tracking is required.

## Run the app

Use `app.py` to verify planning core flow quickly:
```bash
streamlit run app.py
```

Use `dashboard_app.py` for the final portfolio web experience:
```bash
streamlit run dashboard_app.py
```

## Optional IBM WatsonX setup

1. Copy `.env.example` to `.env`.
2. Fill these values:
   - `WATSONX_API_KEY`
   - `WATSONX_URL`
   - `WATSONX_PROJECT_ID`
3. In the app, toggle **Use IBM AI for refinement**.

The application still works without these variables; it falls back to deterministic behavior.
