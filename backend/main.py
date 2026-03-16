from fastapi import FastAPI
from backend.generator.terraform_generator import generate_terraform

app = FastAPI()

@app.post("/generate")
def generate(architecture: dict):
    code = generate_terraform(architecture)
    return {"terraform": code}