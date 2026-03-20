from typing import List, Tuple
from backend.models import InfrastructureSchema


def optimize(plan: InfrastructureSchema) -> Tuple[InfrastructureSchema, List[str]]:
    """
    Apply intelligent optimizations to the architecture plan.
    Returns the (possibly mutated) plan and a list of optimization notes.
    """
    notes = []

    # --- Instance type selection ---------------------------------------------
    if plan.cost_optimized:
        if plan.instance_type != "t3.micro":
            plan.instance_type = "t3.micro"
            notes.append("Instance type set to t3.micro (cost optimized).")
    elif plan.autoscaling or plan.load_balancer:
        plan.instance_type = "t3.small"
        notes.append("Instance type upgraded to t3.small for production workload.")
    else:
        plan.instance_type = "t3.micro"

    # --- Auto-enable autoscaling for large fleets ----------------------------
    if plan.ec2_instances > 2 and not plan.autoscaling:
        plan.autoscaling = True
        notes.append(
            f"Auto Scaling enabled automatically ({plan.ec2_instances} instances detected)."
        )

    # --- Auto-enable load balancer with autoscaling --------------------------
    if plan.autoscaling and not plan.load_balancer:
        plan.load_balancer = True
        notes.append("Load balancer added automatically (required for Auto Scaling).")

    # --- Ensure private subnets for database ---------------------------------
    if plan.database and plan.private_subnets == 0:
        plan.private_subnets = 2
        notes.append("2 private subnets added automatically to host the database securely.")

    # --- Ensure NAT gateway for private subnets ------------------------------
    if plan.private_subnets > 0 and not plan.nat_gateway:
        plan.nat_gateway = True
        notes.append("NAT Gateway added automatically for private subnet internet access.")

    # --- Ensure multi-AZ public subnets for ALB ------------------------------
    if plan.load_balancer and plan.public_subnets < 2:
        plan.public_subnets = 2
        notes.append("Public subnets increased to 2 for ALB multi-AZ requirement.")

    return plan, notes