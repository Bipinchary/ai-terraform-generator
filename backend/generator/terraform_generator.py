import os
from jinja2 import Environment, FileSystemLoader, StrictUndefined

# ── Template environment ───────────────────────────────────────────────────────
current_dir   = os.path.dirname(os.path.abspath(__file__))
template_path = os.path.join(current_dir, "..", "templates")
template_path = os.path.abspath(template_path)

env = Environment(
    loader=FileSystemLoader(template_path),
    undefined=StrictUndefined,      # blow up loudly if a variable is missing
    trim_blocks=True,               # remove newline after {% ... %} blocks
    lstrip_blocks=True,             # strip leading whitespace before {% ... %}
)

# ── Defaults (override via kwargs if needed) ──────────────────────────────────
DEFAULTS = {
    "project_name" : "myproject",
    "region"       : "us-east-1",
    "vpc_cidr"     : "10.0.0.0/16",
    "instance_type": "t2.micro",
    # Amazon Linux 2023 AMI in us-east-1 (update per region as needed)
    "ami_id"       : "ami-0c02fb55956c7d316",
}

# Cycle through a, b, c … for AZ suffixes
_AZ_SUFFIXES = list("abcdef")


def _build_context(architecture: dict, **overrides) -> dict:
    """
    Turn the flat architecture dict produced by InfrastructureSchema
    into the richer context object that main.tf.j2 expects.
    """
    cfg = {**DEFAULTS, **overrides}

    num_subnets   = architecture.get("subnets", 0)
    num_instances = architecture.get("ec2_instances", 0)

    # Build subnet list
    subnets = [
        {
            "index"    : i + 1,
            "cidr"     : f"10.0.{i + 1}.0/24",
            "az_suffix": _AZ_SUFFIXES[i % len(_AZ_SUFFIXES)],
        }
        for i in range(num_subnets)
    ]

    # Distribute instances across subnets round-robin (subnet_index is 1-based)
    instances = []
    for i in range(num_instances):
        subnet_index = (i % num_subnets) + 1 if num_subnets else 1
        instances.append({"index": i + 1, "subnet_index": subnet_index})

    return {
        "project_name" : cfg["project_name"],
        "region"       : cfg["region"],
        "vpc_cidr"     : cfg["vpc_cidr"],
        "instance_type": cfg["instance_type"],
        "ami_id"       : cfg["ami_id"],
        "vpc"          : architecture.get("vpc", False),
        "subnets"      : subnets,
        "ec2_instances": instances,
    }


def generate_terraform(architecture: dict, **overrides) -> str:
    """
    Render main.tf.j2 with the given architecture dict and return
    the Terraform source as a string.  Also writes terraform-output/main.tf.

    Parameters
    ----------
    architecture : dict
        Keys: vpc (bool), subnets (int), ec2_instances (int)
    **overrides :
        Any DEFAULTS key can be overridden, e.g. region="eu-west-1"
    """
    context        = _build_context(architecture, **overrides)
    template       = env.get_template("main.tf.j2")
    terraform_code = template.render(**context)

    out_dir = os.path.join(os.getcwd(), "terraform-output")
    os.makedirs(out_dir, exist_ok=True)

    out_path = os.path.join(out_dir, "main.tf")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(terraform_code)

    return terraform_code