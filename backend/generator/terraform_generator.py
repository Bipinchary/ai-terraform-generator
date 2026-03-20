import os
from jinja2 import Environment, FileSystemLoader, StrictUndefined

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

DEFAULTS = {
    "project_name" : "myproject",
    "region"       : "us-east-1",
    "vpc_cidr"     : "10.0.0.0/16",
    "instance_type": "t3.micro",
}

_AZ_SUFFIXES = list("abcdef")


def _build_context(architecture: dict, **overrides) -> dict:
    cfg = {**DEFAULTS, **overrides}

    num_public    = architecture.get("public_subnets", 0)
    num_private   = architecture.get("private_subnets", 0)
    num_instances = architecture.get("ec2_instances", 0)

    # Public subnets: 10.0.1.x, 10.0.2.x ...
    public_subnets = [
        {
            "index"    : i + 1,
            "cidr"     : f"10.0.{i + 1}.0/24",
            "az_suffix": _AZ_SUFFIXES[i % len(_AZ_SUFFIXES)],
        }
        for i in range(num_public)
    ]

    # Private subnets: 10.0.10.x, 10.0.11.x ... (separate CIDR range)
    private_subnets = [
        {
            "index"    : i + 1,
            "cidr"     : f"10.0.{10 + i}.0/24",
            "az_suffix": _AZ_SUFFIXES[i % len(_AZ_SUFFIXES)],
        }
        for i in range(num_private)
    ]

    # Distribute EC2 instances across public subnets round-robin
    instances = [
        {
            "index"       : i + 1,
            "subnet_index": (i % num_public) + 1 if num_public else 1,
        }
        for i in range(num_instances)
    ]

    return {
        "project_name"  : cfg["project_name"],
        "region"        : cfg["region"],
        "vpc_cidr"      : cfg["vpc_cidr"],
        "instance_type" : architecture.get("instance_type", cfg["instance_type"]),
        "vpc"           : architecture.get("vpc", False),
        "public_subnets": public_subnets,
        "private_subnets": private_subnets,
        "ec2_instances" : instances,
        "autoscaling"   : architecture.get("autoscaling", False),
        "load_balancer" : architecture.get("load_balancer", False),
        "database"      : architecture.get("database", False),
        "db_engine"     : architecture.get("db_engine", "mysql"),
        "nat_gateway"   : architecture.get("nat_gateway", False),
    }


def _write_tfvars(context: dict, out_dir: str) -> None:
    lines = [
        "# ------------------------------------------------------------",
        "# terraform.tfvars — edit to customise your deployment",
        "# ------------------------------------------------------------",
        f'project_name  = "{context["project_name"]}"',
        f'region        = "{context["region"]}"',
        f'vpc_cidr      = "{context["vpc_cidr"]}"',
        f'instance_type = "{context["instance_type"]}"',
    ]
    path = os.path.join(out_dir, "terraform.tfvars")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[GENERATOR] tfvars  → {path}")


def generate_terraform(architecture: dict, **overrides) -> str:
    context        = _build_context(architecture, **overrides)
    template       = env.get_template("main.tf.j2")
    terraform_code = template.render(**context)

    os.makedirs(_OUTPUT_DIR, exist_ok=True)

    main_path = os.path.join(_OUTPUT_DIR, "main.tf")
    with open(main_path, "w", encoding="utf-8") as f:
        f.write(terraform_code)
    print(f"[GENERATOR] main.tf → {main_path}")

    _write_tfvars(context, _OUTPUT_DIR)
    return terraform_code