import os
import json
import re
from typing import Dict

from openai import OpenAI, APIConnectionError, APIStatusError, APITimeoutError
from dotenv import load_dotenv

from backend.models import InfrastructureSchema, PlannerResponse

# --- Load .env using an absolute path anchored to the project root -----------
# This file lives at: <root>/backend/planner/llm_planner.py
# .env lives at:      <root>/.env
_HERE     = os.path.dirname(os.path.abspath(__file__))
_ROOT     = os.path.abspath(os.path.join(_HERE, "..", ".."))
_ENV_PATH = os.path.join(_ROOT, ".env")

load_dotenv(dotenv_path=_ENV_PATH)

HF_API_KEY = os.getenv("HUGGINGFACE_API_KEY")

if not HF_API_KEY:
    raise EnvironmentError(
        f"HUGGINGFACE_API_KEY is not set.\n"
        f"Expected .env at: {_ENV_PATH}\n"
        f"Add this line:    HUGGINGFACE_API_KEY=hf_xxxxxxxxxxxx\n"
        f"Get your token:   https://huggingface.co/settings/tokens"
    )

# HF router — OpenAI-compatible, works with any chat-completion model on the Hub
client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=HF_API_KEY,
)

# Free-tier chat model confirmed to support system prompts + JSON output.
# Easy swaps (all free tier):
#   "Qwen/Qwen2.5-72B-Instruct"          (smarter, slower)
#   "meta-llama/Meta-Llama-3.1-8B-Instruct"  (needs HF access approval)
MODEL = "Qwen/Qwen2.5-7B-Instruct"

# --- System prompts ----------------------------------------------------------
RELEVANCE_SYSTEM = """You are a strict one-word classifier.
Decide whether the user message is related to cloud infrastructure,
AWS resources, networking, servers, or infrastructure-as-code
(Terraform, Pulumi, CDK, CloudFormation, etc.).

Reply with ONLY one word:
  RELEVANT
  IRRELEVANT

No punctuation. No explanation. No markdown. Just the single word."""

PLANNER_SYSTEM = """You are an AWS infrastructure planner.
Convert the user request into a JSON object. Return ONLY raw JSON — no markdown fences, no backticks, no explanation.

Schema:
{
  "relevant": true,
  "vpc": <true|false>,
  "subnets": <integer 0-6>,
  "ec2_instances": <integer 0-20>
}

Rules:
- If the request is NOT about infrastructure, return: {"relevant": false}
- "vpc" must be true if subnets > 0 or ec2_instances > 0
- "subnets" must be >= 1 if ec2_instances > 0
- "a couple" = 2, "a few" = 3, "several" = 4
- When ambiguous, use the minimal safe default"""


# --- API call ----------------------------------------------------------------
def _call_hf(system: str, user_message: str, max_tokens: int = 256) -> str:
    """Call HF router via OpenAI-compatible chat completions. Returns stripped text."""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user_message},
        ],
        max_tokens=max_tokens,
        temperature=0.1,
    )
    return (response.choices[0].message.content or "").strip()


# --- JSON extractor ----------------------------------------------------------
def _extract_json(text: str) -> Dict:
    """Strip comments/fences, pull the first {...} block, and parse it."""
    text = re.sub(r"//.*", "", text)                            # remove // comments
    text = re.sub(r"```[a-z]*", "", text).replace("```", "")   # strip code fences
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in model output: {text!r}")
    return json.loads(match.group())


# --- Main entry point --------------------------------------------------------
def prompt_to_architecture(user_prompt: str) -> PlannerResponse:
    """
    Returns a PlannerResponse:
      - On success   -> PlannerResponse(ok=True,  architecture=InfrastructureSchema(...))
      - On off-topic -> PlannerResponse(ok=False, error="...")
      - On any error -> PlannerResponse(ok=False, error="...")
    """
    # Step 1: relevance guard (cheap 1-word call)
    try:
        verdict = _call_hf(RELEVANCE_SYSTEM, user_prompt, max_tokens=5)
        print(f"[RELEVANCE] {verdict!r}")
    except (APIConnectionError, APITimeoutError) as exc:
        return PlannerResponse(ok=False, error=f"HuggingFace API unreachable: {exc}")
    except APIStatusError as exc:
        return PlannerResponse(ok=False, error=f"HuggingFace API error {exc.status_code}: {exc.message}")
    except Exception as exc:
        return PlannerResponse(ok=False, error=f"LLM call failed: {exc}")

    if not verdict.upper().startswith("RELEVANT"):
        return PlannerResponse(
            ok=False,
            error=(
                "Your request doesn't appear to be related to cloud infrastructure. "
                "Please describe what AWS resources you need, for example: "
                "'I need a VPC with 2 subnets and 3 EC2 instances.'"
            ),
        )

    # Step 2: plan -- natural language -> JSON
    try:
        raw = _call_hf(PLANNER_SYSTEM, user_prompt, max_tokens=150)
        print(f"[PLANNER RAW] {raw!r}")
        data = _extract_json(raw)
    except (APIConnectionError, APITimeoutError) as exc:
        return PlannerResponse(ok=False, error=f"HuggingFace API unreachable: {exc}")
    except APIStatusError as exc:
        return PlannerResponse(ok=False, error=f"HuggingFace API error {exc.status_code}: {exc.message}")
    except (ValueError, json.JSONDecodeError) as exc:
        return PlannerResponse(ok=False, error=f"LLM returned unparseable output: {exc}")
    except Exception as exc:
        return PlannerResponse(ok=False, error=f"LLM call failed: {exc}")

    # Double-check relevance flag from planner output
    if not data.get("relevant", True):
        return PlannerResponse(ok=False, error="Not an infrastructure-related request.")

    data.pop("relevant", None)

    # Step 3: Pydantic validation
    try:
        architecture = InfrastructureSchema(**data)
    except Exception as exc:
        return PlannerResponse(ok=False, error=f"Schema validation failed: {exc}")

    return PlannerResponse(ok=True, architecture=architecture)