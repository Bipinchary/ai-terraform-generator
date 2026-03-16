from fastapi import FastAPI
from backend.generator.terraform_generator import generate_terraform
from backend.planner.llm_planner import prompt_to_architecture

app = FastAPI()

@app.post("/generate")

def generate(prompt: str):

    architecture = prompt_to_architecture(prompt)

    terraform_code = generate_terraform(architecture)

    return {
        "architecture": architecture,
        "terraform": terraform_code
    }