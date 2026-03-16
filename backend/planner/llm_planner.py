import requests
import json
import re

OLLAMA_URL = "http://localhost:11434/api/generate"


SYSTEM_PROMPT = """
Convert the user request into infrastructure JSON.

Return ONLY JSON.

Schema:
{
 "vpc": boolean,
 "subnets": number,
 "ec2_instances": number
}
"""


def extract_json(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return json.loads(match.group())


def prompt_to_architecture(prompt):

    full_prompt = SYSTEM_PROMPT + "\nUser request: " + prompt

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": "llama3",
            "prompt": full_prompt,
            "stream": False
        }
    )

    result = response.json()["response"]

    return extract_json(result)