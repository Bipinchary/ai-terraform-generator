from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.generator.terraform_generator import generate_terraform
from backend.planner.llm_planner import prompt_to_architecture
from backend.validator.infra_validator import validate
from backend.core.optimizer.optimizer import optimize

app = FastAPI(
    title="AI Terraform Generator",
    description="Converts natural-language infrastructure requests into production-ready Terraform.",
    version="2.0.0",
)


class GenerateRequest(BaseModel):
    prompt: str


@app.post("/generate")
def generate(request: GenerateRequest):
    prompt = request.prompt.strip()

    if not prompt:
        return JSONResponse(status_code=400, content={"error": "Prompt cannot be empty."})

    # Step 1: LLM plan
    result = prompt_to_architecture(prompt)
    if not result.ok:
        return JSONResponse(status_code=400, content={"error": result.error})

    # Step 2: Optimize
    architecture, optimizations, decisions = optimize(result.architecture)

    # Step 3: Validate
    warnings = validate(architecture)

    # Step 4: Generate Terraform
    try:
        terraform_code = generate_terraform(architecture.model_dump())
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"error": f"Terraform generation failed: {exc}"},
        )

    return {
        "architecture" : architecture.model_dump(),
        "optimizations": optimizations,
        "decisions"    : decisions,
        "warnings"     : warnings,
        "terraform"    : terraform_code,
    }