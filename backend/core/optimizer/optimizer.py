from typing import Tuple, List, Dict
from backend.models import InfrastructureSchema
from backend.core.optimizer.engine import run_rules


def optimize(plan: InfrastructureSchema) -> Tuple[InfrastructureSchema, List[str], List[Dict]]:
    plan, decisions, notes = run_rules(plan)
    return plan, notes, decisions