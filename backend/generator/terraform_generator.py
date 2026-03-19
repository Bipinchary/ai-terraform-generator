import os
from jinja2 import Environment, FileSystemLoader, StrictUndefined

# --- Paths anchored to this file's location ----------------------------------
# This file lives at: <root>/backend/generator/terraform_generator.py
# Templates live at:  <root>/backend/generator/templates/
# Output goes to:     <root>/terraform-output/
_HERE         = os.path.dirname(os.path.abspath(__file__))
_TEMPLATE_DIR = os.path.join(_HERE, "templates")
_ROOT         = os.path.abspath(os.path.join(_HERE, "..", ".."))
_OUTPUT_DIR   = os.path.join(_ROOT, "terraform-output")

env = Environment(
    loader=FileSystemLoader(_TEMPLATE_DIR),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)

# --- Defaults ----------------------------------------------------------------
DEFAULTS = {
    "project_name" : "myproject",
    "region"       : "us-east-1",
    "vpc_cidr"     : "10.0.0.0/16",
    "instance_type": "t2.micro",
}

_AZ_SUFFIXES = list("abcdef")


def _build_context(architecture: dict, **overrides) -> dict:
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


def _write_tfvars(context: dict, out_dir: str) -> None:
    """Write a terraform.tfvars so the user can customise without editing main.tf."""
    lines = [
        "# ------------------------------------------------------------",
        "# terraform.tfvars — override any default here",
        "# ------------------------------------------------------------",
        f'project_name  = "{context["project_name"]}"',
        f'region        = "{context["region"]}"',
        f'vpc_cidr      = "{context["vpc_cidr"]}"',
        f'instance_type = "{context["instance_type"]}"',
    ]
    path = os.path.join(out_dir, "terraform.tfvars")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[GENERATOR] tfvars written to : {path}")


def generate_terraform(architecture: dict, **overrides) -> str:
    """
    Render main.tf.j2, write main.tf + terraform.tfvars to terraform-output/.
    Returns the rendered Terraform source as a string.
    """
    context        = _build_context(architecture, **overrides)
    template       = env.get_template("main.tf.j2")
    terraform_code = template.render(**context)

    os.makedirs(_OUTPUT_DIR, exist_ok=True)

    # main.tf
    main_path = os.path.join(_OUTPUT_DIR, "main.tf")
    with open(main_path, "w", encoding="utf-8") as f:
        f.write(terraform_code)
    print(f"[GENERATOR] main.tf written to  : {main_path}")

    # terraform.tfvars
    _write_tfvars(context, _OUTPUT_DIR)

    return terraform_code