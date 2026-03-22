from typing import List, Tuple
from backend.models import InfrastructureSchema
from backend.core.optimizer.rules import (
    rule_autoscaling_requires_lb,
    rule_database_private_subnet,
    rule_private_subnet_needs_nat,
    rule_lb_requires_multiple_subnets,
    rule_large_ec2_needs_autoscaling,
    rule_instance_type_selection,
)

RULES = [
    rule_large_ec2_needs_autoscaling,
    rule_autoscaling_requires_lb,
    rule_database_private_subnet,
    rule_private_subnet_needs_nat,
    rule_lb_requires_multiple_subnets,
    rule_instance_type_selection,
]


def run_rules(plan: InfrastructureSchema) -> Tuple[InfrastructureSchema, List[dict], List[str]]:
    decisions = []
    notes = []

    for rule in RULES:
        result = rule(plan)

        if result:
            decisions.append(result)
            notes.append(result["action"].replace("_", " ").capitalize())

    return plan, decisions, notes