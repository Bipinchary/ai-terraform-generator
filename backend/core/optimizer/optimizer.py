from typing import Tuple, List
from backend.models import InfrastructureSchema
from backend.core.optimizer.engine import run_rules


def optimize(plan: InfrastructureSchema) -> Tuple[InfrastructureSchema, List[str], List[dict]]:
    plan, decisions, notes = run_rules(plan)
    return plan, notes, decisions