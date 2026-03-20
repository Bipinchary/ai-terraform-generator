import os
import json
import re
from typing import Dict

from openai import OpenAI, APIConnectionError, APIStatusError, APITimeoutError
from dotenv import load_dotenv

from backend.models import InfrastructureSchema, PlannerResponse

# --- Load .env ---------------------------------------------------------------
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

client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=HF_API_KEY,
)
MODEL = "Qwen/Qwen2.5-7B-Instruct"

# --- Prompts -----------------------------------------------------------------
RELEVANCE_SYSTEM = """You are a strict one-word classifier.
Decide whether the user message is related to cloud infrastructure,
AWS resources, networking, servers, or infrastructure-as-code
(Terraform, Pulumi, CDK, CloudFormation, etc.).

Reply with ONLY one word:
  RELEVANT
  IRRELEVANT

No punctuation. No explanation. No markdown. Just the single word."""

PLANNER_SYSTEM = """You are an expert AWS solutions architect.
Convert the user request into a JSON architecture plan.
Return ONLY raw JSON — no markdown, no backticks, no explanation.

Schema:
{
  "relevant": true,
  "vpc": <true|false>,
  "public_subnets": <integer 0-6>,
  "private_subnets": <integer 0-6>,
  "ec2_instances": <integer 0-20>,
  "autoscaling": <true|false>,
  "load_balancer": <true|false>,
  "database": <true|false>,
  "db_engine": <"mysql"|"postgres">,
  "nat_gateway": <true|false>,
  "cost_optimized": <true|false>
}

Rules:
- If NOT infrastructure: return {"relevant": false}
- "scalable" or "high availability" → autoscaling=true, load_balancer=true
- "public traffic" or "web app" → load_balancer=true
- "database" or "RDS" or "MySQL" or "Postgres" → database=true
- "private" or "secure backend" → private_subnets >= 1
- "cost" or "cheap" or "minimal" → cost_optimized=true
- "a couple"=2, "a few"=3, "several"=4
- When ambiguous, use minimal safe defaults"""


# --- Helpers -----------------------------------------------------------------
def _call_hf(system: str, user_message: str, max_tokens: int = 300) -> str:
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


def _extract_json(text: str) -> Dict:
    text = re.sub(r"//.*", "", text)
    text = re.sub(r"```[a-z]*", "", text).replace("```", "")
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON found in model output: {text!r}")
    return json.loads(match.group())


# --- Main entry point --------------------------------------------------------
def prompt_to_architecture(user_prompt: str) -> PlannerResponse:
    # Step 1: relevance guard
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
                "'Deploy a scalable web app with a database and load balancer.'"
            ),
        )

    # Step 2: plan → JSON
    try:
        raw = _call_hf(PLANNER_SYSTEM, user_prompt, max_tokens=300)
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

    if not data.get("relevant", True):
        return PlannerResponse(ok=False, error="Not an infrastructure-related request.")

    data.pop("relevant", None)

    # Step 3: Pydantic validation + auto-correction
    try:
        architecture = InfrastructureSchema(**data)
    except Exception as exc:
        return PlannerResponse(ok=False, error=f"Schema validation failed: {exc}")

    return PlannerResponse(ok=True, architecture=architecture)