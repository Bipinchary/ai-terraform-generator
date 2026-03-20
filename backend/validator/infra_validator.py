from typing import List
from backend.models import InfrastructureSchema


def validate(plan: InfrastructureSchema) -> List[str]:
    """
    Returns a list of warning strings for any architecture issues.
    Warnings are informational — they do not block generation.
    """
    warnings = []

    # --- Security warnings ---------------------------------------------------
    if plan.ec2_instances > 0 and not plan.load_balancer:
        warnings.append(
            "No load balancer: instances are directly exposed. "
            "Consider adding a load balancer for production workloads."
        )

    if plan.database and not plan.db_private:
        warnings.append(
            "Database is not in a private subnet — this is a security risk. "
            "RDS instances should never be publicly accessible."
        )

    if plan.public_subnets > 0 and plan.private_subnets == 0 and plan.database:
        warnings.append(
            "All subnets are public but a database is requested. "
            "Private subnets will be auto-added to protect the database."
        )

    # --- Networking warnings -------------------------------------------------
    if plan.private_subnets > 0 and not plan.nat_gateway:
        warnings.append(
            "Private subnets exist without a NAT Gateway — instances in private "
            "subnets will have no outbound internet access."
        )

    if plan.load_balancer and plan.public_subnets < 2:
        warnings.append(
            "An ALB requires at least 2 subnets in different AZs. "
            "Public subnets will be auto-increased to 2."
        )

    # --- Scaling warnings ----------------------------------------------------
    if plan.ec2_instances > 3 and not plan.autoscaling:
        warnings.append(
            f"You have {plan.ec2_instances} fixed EC2 instances but no Auto Scaling. "
            "Consider enabling autoscaling for better resilience and cost control."
        )

    if plan.autoscaling and not plan.load_balancer:
        warnings.append(
            "Auto Scaling is enabled but there is no load balancer — "
            "new instances will not receive traffic automatically."
        )

    # --- Cost warnings -------------------------------------------------------
    if plan.nat_gateway and plan.cost_optimized:
        warnings.append(
            "NAT Gateway costs ~$32/month plus data transfer fees. "
            "Consider using a NAT instance for lower-cost environments."
        )

    if plan.database and plan.cost_optimized:
        warnings.append(
            "RDS costs money even when idle. "
            "Consider Aurora Serverless or a db.t3.micro for dev/test environments."
        )

    return warnings 