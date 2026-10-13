import os
from pathlib import Path
import sys

from dotenv import load_dotenv
from google import genai


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")
api_key = os.getenv("GEMINI_API_KEY")
if not api_key or not api_key.strip():
    raise RuntimeError("GEMINI_API_KEY is missing or empty.")

client = genai.Client(api_key=api_key.strip())
prompt = "Xin chào, bạn có hoạt động không?"
models_to_try = [
    "gemini-2.5-flash",
    "gemini-1.5-flash",
    "gemini-3.8-flash",
]

for index, model in enumerate(models_to_try):
    try:
        response = client.models.generate_content(model=model, contents=prompt)
    except Exception as exc:
        safe_error = str(exc).replace(api_key.strip(), "[REDACTED]")
        print(f"{model} failed: {safe_error}")
        if index == len(models_to_try) - 1:
            raise RuntimeError("All configured Gemini model attempts failed.") from None
        print(f"Retrying with {models_to_try[index + 1]}.")
    else:
        print("Key loaded: yes")
        print(f"Model: {model}")
        print("Response:", response.text)
        break
