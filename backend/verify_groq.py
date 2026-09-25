"""Verify the local Groq configuration without exposing the API key."""

import os
import sys

import httpx

from app.config import load_environment


def main() -> int:
    load_environment()
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
    configured_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b").strip()

    if not api_key or api_key == "replace_with_your_groq_key":
        print("Groq is not configured yet.")
        print("Paste your key after GROQ_API_KEY in backend/.env, then run this command again.")
        return 1

    try:
        response = httpx.get(
            f"{base_url}/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=20.0,
        )
    except httpx.RequestError as error:
        print(f"Could not reach Groq: {error}")
        return 1

    if response.status_code != 200:
        print(f"Groq rejected the configuration (HTTP {response.status_code}).")
        print("Check GROQ_API_KEY and GROQ_BASE_URL in backend/.env.")
        return 1

    payload = response.json()
    model_ids = {
        item.get("id")
        for item in payload.get("data", [])
        if isinstance(item, dict) and item.get("id")
    }
    print("Groq API key accepted.")
    if configured_model in model_ids:
        print(f"Configured model is available: {configured_model}")
    else:
        print(f"Configured model was not listed: {configured_model}")
        print("Change GROQ_MODEL in backend/.env to one of the IDs returned by Groq.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
