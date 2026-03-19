import os
from jinja2 import Environment, FileSystemLoader, StrictUndefined

# --- Paths anchored to this file's location ----------------------------------
# This file lives at: <root>/backend/generator/terraform_generator.py
# Templates live at:  <root>/backend/generator/templates/
# Output goes to:     <root>/terraform-output/main.tf
_HERE         = os.path.dirname(os.path.abspath(__file__))
_TEMPLATE_DIR = os.path.join(_HERE, "templates")
_ROOT         = os.path.abspath(os.path.join(_HERE, "..", ".."))
_OUTPUT_DIR   = os.path.join(_ROOT, "terraform-output")

env = Environment(
    loader=FileSystemLoader(_TEMPLATE_DIR),
    undefined=StrictUndefined,   # blow up loudly if a variable is missing
    trim_blocks=True,            # remove newline after {% ... %} blocks
    lstrip_blocks=True,          # strip leading whitespace before {% ... %}
)

# --- Defaults (override via kwargs if needed) --------------------------------
DEFAULTS = {
    "project_name" : "myproject",
    "region"       : "us-east-1",
    "vpc_cidr"     : "10.0.0.0/16",
    "instance_type": "t2.micro",
}

_AZ_SUFFIXES = list("abcdef")


def _build_context(architecture: dict, **overrides) -> dict:
    """
    Turn the flat architecture dict from InfrastructureSchema
    into the richer context object that main.tf.j2 expects.
    """
    cfg = {**DEFAULTS, **overrides}

    num_subnets   = architecture.get("subnets", 0)
    num_instances = architecture.get("ec2_instances", 0)

    subnets = [
        {
            "index"    : i + 1,
            "cidr"     : f"10.0.{i + 1}.0/24",
            "az_suffix": _AZ_SUFFIXES[i % len(_AZ_SUFFIXES)],
        }
        for i in range(num_subnets)
    ]

    instances = [
        {
            "index"       : i + 1,
            "subnet_index": (i % num_subnets) + 1 if num_subnets else 1,
        }
        for i in range(num_instances)
    ]

    return {
        "project_name" : cfg["project_name"],
        "region"       : cfg["region"],
        "vpc_cidr"     : cfg["vpc_cidr"],
        "instance_type": cfg["instance_type"],
        "vpc"          : architecture.get("vpc", False),
        "subnets"      : subnets,
        "ec2_instances": instances,
    }


def generate_terraform(architecture: dict, **overrides) -> str:
    """
    Render main.tf.j2 and write the result to <root>/terraform-output/main.tf.
    Returns the rendered Terraform source as a string.
    """
    context        = _build_context(architecture, **overrides)
    template       = env.get_template("main.tf.j2")
    terraform_code = template.render(**context)

    # Always write relative to the project root, never os.getcwd()
    os.makedirs(_OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(_OUTPUT_DIR, "main.tf")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(terraform_code)

    print(f"[GENERATOR] Written to: {out_path}")
    return terraform_code