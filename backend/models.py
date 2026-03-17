from pydantic import BaseModel, Field, model_validator
from typing import Optional


class InfrastructureSchema(BaseModel):
    """
    Validated representation of the infrastructure the LLM planned.

    Business rules enforced here (not just in the prompt):
    - Subnets and EC2 instances implicitly require a VPC → auto-correct vpc=True.
    - EC2 instances require at least one subnet → auto-correct subnets to 1.
    """

    vpc: bool = Field(
        default=False,
        description="Whether to create an AWS VPC.",
    )
    subnets: int = Field(
        default=0,
        ge=0,
        le=6,
        description="Number of subnets to create (0–6).",
    )
    ec2_instances: int = Field(
        default=0,
        ge=0,
        le=20,
        description="Number of EC2 instances to create (0–20).",
    )

    @model_validator(mode="after")
    def enforce_dependencies(self) -> "InfrastructureSchema":
        # Instances need a subnet
        if self.ec2_instances > 0 and self.subnets == 0:
            self.subnets = 1

        # Subnets (and therefore instances) need a VPC
        if self.subnets > 0 and not self.vpc:
            self.vpc = True

        return self


class PlannerResponse(BaseModel):
    """Wrapper returned by prompt_to_architecture()."""

    ok: bool
    architecture: Optional[InfrastructureSchema] = None
    error: Optional[str] = None