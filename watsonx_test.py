from __future__ import annotations

import json
import os
import sys
from pprint import pprint
from typing import Any

from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference


def extract_text(response: Any) -> str:
    if isinstance(response, str):
        return response
    if isinstance(response, dict):
        direct_text = response.get("generated_text")
        if isinstance(direct_text, str):
            return direct_text

        results = response.get("results")
        if isinstance(results, list) and results:
            first = results[0]
            if isinstance(first, str):
                return first
            if isinstance(first, dict):
                for key in ("generated_text", "output_text", "text"):
                    value = first.get(key)
                    if isinstance(value, str):
                        return value

        choices = response.get("choices")
        if isinstance(choices, list) and choices:
            first_choice = choices[0]
            if isinstance(first_choice, dict):
                text = first_choice.get("text")
                if isinstance(text, str):
                    return text
    return ""


def main() -> int:
    required = ["WATSONX_API_KEY", "WATSONX_URL", "WATSONX_PROJECT_ID"]
    missing = [key for key in required if not os.environ.get(key)]
    if missing:
        print("Missing required environment variables:", ", ".join(missing))
        return 1

    try:
        credentials = Credentials(
            api_key=os.environ["WATSONX_API_KEY"],
            url=os.environ["WATSONX_URL"],
        )
        model = ModelInference(
            model_id="ibm/granite-4-h-small",
            credentials=credentials,
            project_id=os.environ["WATSONX_PROJECT_ID"],
        )

        prompt = """
You are an AI that returns structured JSON.

Return a valid JSON object with this schema:

{
"status": "string",
"confidence": "number"
}

Return ONLY JSON.
Do not include markdown or explanations.
"""
        params = {
            "max_new_tokens": 150,
            "temperature": 0.2,
        }
        response = model.generate(prompt=prompt, params=params)

        print("Raw response:")
        pprint(response)
        print("\nExtracted text:")
        generated_text = extract_text(response)
        print(generated_text)

        import re
        import json

        match = re.search(r"{.*}", generated_text, flags=re.DOTALL)
        if match:
            parsed = json.loads(match.group())
            print("Parsed JSON:", parsed)
        else:
            print("No valid JSON found.")
        return 0
    except Exception as exc:
        print(f"WatsonX connectivity test failed: {exc.__class__.__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
