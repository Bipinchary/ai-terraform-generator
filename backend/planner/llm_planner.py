import requests
import json
import re
from backend.models import InfrastructureSchema, PlannerResponse

OLLAMA_URL = "http://localhost:11434/api/generate"

# ── Prompt 1: Guard – is this an infra request at all? ────────────────────────
RELEVANCE_PROMPT = """You are a strict classifier.
Decide whether the user message is related to cloud infrastructure, 
AWS resources, networking, servers, or infrastructure-as-code (Terraform, Pulumi, CDK, etc.).

Reply with ONLY one word — either:
  RELEVANT
  IRRELEVANT

No punctuation. No explanation. Just the single word."""

# ── Prompt 2: Planner – convert infra request → JSON ─────────────────────────
PLANNER_SYSTEM_PROMPT = """You are an AWS infrastructure planner.
Your ONLY job is to convert a natural-language infrastructure request into a
strict JSON object. 

Rules:
- Always return ONLY a raw JSON object — no markdown, no backticks, no explanation.
- "vpc" must be true whenever subnets or EC2 instances are requested (subnets require a VPC).
- "subnets" must be >= 1 whenever ec2_instances > 0 (instances need a subnet).
- Cap "subnets" at 6 and "ec2_instances" at 20 unless the user explicitly asks for more.
- If the user says "a couple", interpret as 2; "a few" as 3; "several" as 4-5.
- If information is ambiguous, choose the minimal safe default.

Return exactly this schema:
{
  "vpc": <true | false>,
  "subnets": <integer 0-6>,
  "ec2_instances": <integer 0-20>
}"""


def _call_ollama(prompt: str) -> str:
    """Raw call to the local Ollama endpoint. Raises on HTTP error."""
    response = requests.post(
        OLLAMA_URL,
        json={"model": "llama3", "prompt": prompt, "stream": False},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["response"].strip()


def _is_infra_request(user_prompt: str) -> bool:
    """Return True only if the LLM thinks the prompt is infra-related."""
    full_prompt = RELEVANCE_PROMPT + f"\n\nUser message: {user_prompt}"
    answer = _call_ollama(full_prompt).upper()
    return answer.startswith("RELEVANT")


def _extract_json(text: str) -> dict:
    """Pull the first {...} block from the model output and parse it."""
    match = re.search(r"\{.*?\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in model output: {text!r}")
    return json.loads(match.group())


def prompt_to_architecture(user_prompt: str) -> PlannerResponse:
    """
    Main entry point.

    Returns a PlannerResponse:
      - On success  → PlannerResponse(ok=True,  architecture=InfrastructureSchema(...))
      - On off-topic → PlannerResponse(ok=False, error="...")
      - On any error → PlannerResponse(ok=False, error="...")
    """
    # ── Step 1: relevance guard ────────────────────────────────────────────────
    try:
        if not _is_infra_request(user_prompt):
            return PlannerResponse(
                ok=False,
                error=(
                    "Your request doesn't appear to be related to cloud infrastructure. "
                    "Please describe what AWS resources you need — for example: "
                    "'I need a VPC with 2 subnets and 3 EC2 instances.'"
                ),
            )
    except requests.RequestException as exc:
        return PlannerResponse(ok=False, error=f"LLM service unavailable: {exc}")

    # ── Step 2: convert prompt → JSON ──────────────────────────────────────────
    try:
        full_prompt = PLANNER_SYSTEM_PROMPT + f"\n\nUser request: {user_prompt}"
        raw = _call_ollama(full_prompt)
        data = _extract_json(raw)
    except requests.RequestException as exc:
        return PlannerResponse(ok=False, error=f"LLM service unavailable: {exc}")
    except (ValueError, json.JSONDecodeError) as exc:
        return PlannerResponse(ok=False, error=f"LLM returned unparseable output: {exc}")

    # ── Step 3: validate with Pydantic ─────────────────────────────────────────
    try:
        architecture = InfrastructureSchema(**data)
    except Exception as exc:          # pydantic ValidationError
        return PlannerResponse(ok=False, error=f"Schema validation failed: {exc}")

    return PlannerResponse(ok=True, architecture=architecture)