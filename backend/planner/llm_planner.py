import requests
import json
import re
from typing import Dict

from backend.models import InfrastructureSchema, PlannerResponse

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "phi3"

# ── Prompt ──────────────────────────────────────────────────
SYSTEM_PROMPT = """You are an AWS infrastructure planner.

Return ONLY valid JSON.
Do NOT include:
- comments
- explanations
- words like integer()
- any text outside JSON

Rules:
- If not infrastructure → {"relevant": false}
- Otherwise return:

{
  "relevant": true,
  "vpc": true or false,
  "subnets": number,
  "ec2_instances": number
}

Constraints:
- Use ONLY numbers (e.g., 2, 3, 4) — NOT words or functions
- vpc must be true if subnets > 0 or ec2_instances > 0
- subnets >= 1 if ec2_instances > 0
- "a couple" = 2, "a few" = 3

Your output MUST be valid JSON parsable by json.loads().
"""

# ── Call Ollama ─────────────────────────────────────────────
def _call_ollama(prompt: str) -> str:
    try:
        full_prompt = SYSTEM_PROMPT + "\n\nUser request: " + prompt

        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": full_prompt,
                "stream": False
            },
            timeout=60,
        )

        response.raise_for_status()
        return response.json()["response"].strip()

    except requests.RequestException as exc:
        raise RuntimeError(f"Ollama error: {exc}")


# ── Extract JSON safely ─────────────────────────────────────
def _extract_json(text: str) -> Dict:
    # Remove comments like // ...
    text = re.sub(r"//.*", "", text)

    # Replace integer(3) → 3
    text = re.sub(r"integer\((\d+)\)", r"\1", text)

    # Extract JSON block
    match = re.search(r"\{.*?\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON found: {text}")

    return json.loads(match.group())


# ── Main function ───────────────────────────────────────────
def prompt_to_architecture(user_prompt: str) -> PlannerResponse:
    try:
        raw_output = _call_ollama(user_prompt)

        # Debug (very useful for phi3)
        print("RAW LLM OUTPUT:", raw_output)

        data = _extract_json(raw_output)

        # ── Relevance check ───────────────────────────────
        if not data.get("relevant", False):
            return PlannerResponse(
                ok=False,
                error="Not an infrastructure-related request"
            )

        # Remove helper field
        data.pop("relevant", None)

        # ── Validate schema ───────────────────────────────
        architecture = InfrastructureSchema(**data)

        return PlannerResponse(ok=True, architecture=architecture)

    except RuntimeError as exc:
        return PlannerResponse(ok=False, error=str(exc))

    except (ValueError, json.JSONDecodeError) as exc:
        return PlannerResponse(
            ok=False,
            error=f"Invalid JSON from model: {exc}"
        )

    except Exception as exc:
        return PlannerResponse(
            ok=False,
            error=f"Validation failed: {exc}"
        )