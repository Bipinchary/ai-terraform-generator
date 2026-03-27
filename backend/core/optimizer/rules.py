from typing import Optional, Dict, Callable
from backend.models import InfrastructureSchema




class Rule:
    def __init__(self, name: str, priority: int, func: Callable):
        self.name = name
        self.priority = priority
        self.func = func

    def apply(self, plan: InfrastructureSchema) -> Optional[Dict]:
        return self.func(plan)


def rule_autoscaling_requires_lb(plan: InfrastructureSchema) -> Optional[Dict]:
    if plan.autoscaling and not plan.load_balancer:
        # Skip LB if cost optimized
        if plan.cost_optimized:
            return None

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

def rule_secure_database(plan: InfrastructureSchema) -> Optional[Dict]:
    if plan.database and not plan.db_private:
        plan.db_private = True
        return {
            "action": "secure_database",
            "reason": "Database must not be publicly accessible"
        }

def rule_private_subnet_needs_nat(plan: InfrastructureSchema) -> Optional[Dict]:
    
    if plan.cost_optimized:
        return None

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
        if plan.instance_type != "t3.micro":
            plan.instance_type = "t3.micro"
            return {
                "action": "choose_instance_type",
                "reason": "Cost optimization requested"
            }
        return None

    if (plan.autoscaling or plan.load_balancer) and plan.instance_type == "t3.micro":
        plan.instance_type = "t3.small"
        return {
            "action": "upgrade_instance_type",
            "reason": "Production workload requires better performance"
        }

    return None
    


RULES = [
    Rule("secure_db_rule", 5, rule_secure_database),

    Rule("database_rule", 10, rule_database_private_subnet),

    Rule("ec2_scaling_rule", 20, rule_large_ec2_needs_autoscaling),

    Rule("autoscaling_lb_rule", 30, rule_autoscaling_requires_lb),

    Rule("nat_rule", 40, rule_private_subnet_needs_nat),

    Rule("lb_subnet_rule", 50, rule_lb_requires_multiple_subnets),

    Rule("instance_type_rule", 60, rule_instance_type_selection),
]   