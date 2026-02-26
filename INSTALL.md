# Installation Guide

## Requirements

- Python 3.10+
- pip
- IBM WatsonX credentials (for AI integration)

---

## Setup

Clone repository:

git clone https://github.com/your-username/syllabus-to-action-ai.git
cd syllabus-to-action-ai

Install Streamlit:

python -m pip install streamlit

Install dependencies:

python -m pip install -r requirements.txt

## IBM AI Setup

Create a WatsonX API key:

1) Sign in to IBM Cloud and open WatsonX.
2) Create or select a WatsonX project.
3) Generate an API key for your account or service credentials.

Store the key in a .env file:

WATSONX_API_KEY=your_api_key_here
WATSONX_URL=https://your-watsonx-endpoint

Configure the Granite model name:

- Set the model ID in ai/engine.py (e.g., "granite-text-v1").
- If your org uses a different model ID, replace it accordingly.

Required environment variables:

- WATSONX_API_KEY
- WATSONX_URL

Run locally:

streamlit run app.py
