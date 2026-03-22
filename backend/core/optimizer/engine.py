from typing import List, Tuple, Dict
from backend.models import InfrastructureSchema
from backend.core.optimizer.rules import RULES


def run_rules(plan: InfrastructureSchema) -> Tuple[InfrastructureSchema, List[Dict], List[str]]:
    decisions = []
    notes = []

    # 1. Sort rules by priority
    sorted_rules = sorted(RULES, key=lambda r: r.priority)

    # 2. Run multiple passes (important)
    for _ in range(3):  # prevents infinite loops
        for rule in sorted_rules:
            result = rule.apply(plan)

            if result:
                decisions.append(result)
                notes.append(f"{rule.name} applied")

    return plan, decisions, notes