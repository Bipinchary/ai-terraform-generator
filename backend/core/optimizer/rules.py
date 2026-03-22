from typing import Optional, Dict
from backend.models import InfrastructureSchema


def rule_autoscaling_requires_lb(plan: InfrastructureSchema) -> Optional[Dict]:
    if plan.autoscaling and not plan.load_balancer:
        plan.load_balancer = True
        return {
            "action": "add_load_balancer",
            "reason": "Auto Scaling requires a load balancer to distribute traffic"
        }


def rule_database_private_subnet(plan: InfrastructureSchema) -> Optional[Dict]:
    if plan.database and plan.private_subnets == 0:
        plan.private_subnets = 2
        return {
            "action": "add_private_subnets",
            "reason": "Database should not be publicly accessible"
        }


def rule_private_subnet_needs_nat(plan: InfrastructureSchema) -> Optional[Dict]:
    if plan.private_subnets > 0 and not plan.nat_gateway:
        plan.nat_gateway = True
        return {
            "action": "add_nat_gateway",
            "reason": "Private subnets need outbound internet access"
        }


def rule_lb_requires_multiple_subnets(plan: InfrastructureSchema) -> Optional[Dict]:
    if plan.load_balancer and plan.public_subnets < 2:
        plan.public_subnets = 2
        return {
            "action": "increase_public_subnets",
            "reason": "Load balancer requires at least 2 subnets across AZs"
        }


def rule_large_ec2_needs_autoscaling(plan: InfrastructureSchema) -> Optional[Dict]:
    if plan.ec2_instances > 2 and not plan.autoscaling:
        plan.autoscaling = True
        return {
            "action": "enable_autoscaling",
            "reason": f"{plan.ec2_instances} instances detected — enabling autoscaling for resilience"
        }


def rule_instance_type_selection(plan: InfrastructureSchema) -> Optional[Dict]:
    if plan.cost_optimized:
        plan.instance_type = "t3.micro"
        return {
            "action": "choose_instance_type",
            "reason": "Cost optimization requested"
        }

    if plan.autoscaling or plan.load_balancer:
        plan.instance_type = "t3.small"
        return {
            "action": "upgrade_instance_type",
            "reason": "Production workload requires better performance"
        }