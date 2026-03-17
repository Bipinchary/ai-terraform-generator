from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.generator.terraform_generator import generate_terraform
from backend.planner.llm_planner import prompt_to_architecture

app = FastAPI(
    title="AI Terraform Generator",
    description="Converts natural-language infrastructure requests into Terraform code.",
    version="1.0.0",
)


class GenerateRequest(BaseModel):
    prompt: str


@app.post("/generate")
def generate(request: GenerateRequest):
    """
    Accept a plain-English infrastructure description and return:
      - the structured architecture plan
      - the rendered Terraform code

    Returns HTTP 400 for off-topic / invalid prompts so the server never crashes.
    """
    prompt = request.prompt.strip()

    if not prompt:
        return JSONResponse(
            status_code=400,
            content={"error": "Prompt cannot be empty."},
        )

    # ── Plan ──────────────────────────────────────────────────────────────────
    result = prompt_to_architecture(prompt)

    if not result.ok:
        return JSONResponse(
            status_code=400,
            content={"error": result.error},
        )

    # ── Generate ──────────────────────────────────────────────────────────────
    architecture = result.architecture
    try:
        terraform_code = generate_terraform(architecture.model_dump())
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"error": f"Terraform generation failed: {exc}"},
        )

    return {
        "architecture": architecture.model_dump(),
        "terraform": terraform_code,
    }