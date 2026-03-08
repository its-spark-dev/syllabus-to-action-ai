# Installation Guide

## Requirements

- Python 3.10+
- pip or `python -m pip`

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

## Optional IBM WatsonX setup

Create a `.env` file from `.env.example` and set:

- `WATSONX_API_KEY`
- `WATSONX_URL`

Then enable **Use IBM AI for refinement** in the UI.
