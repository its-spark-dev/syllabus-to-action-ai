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

빠른 실행을 원하면 `Makefile`로도 동일하게 실행할 수 있습니다.
```bash
make setup
```

## Run

```bash
streamlit run app.py
```

또는
```bash
make run
```

## Optional IBM WatsonX setup

Create a `.env` file from `.env.example` and set:

- `WATSONX_API_KEY`
- `WATSONX_URL`

Then enable **Use IBM AI for refinement** in the UI.
