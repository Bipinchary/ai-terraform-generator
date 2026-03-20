from pydantic import BaseModel, Field, model_validator
from typing import Optional, List


class InfrastructureSchema(BaseModel):

    # --- Core networking ---
    vpc: bool = Field(default=False, description="Create a VPC")
    public_subnets: int = Field(default=0, ge=0, le=6, description="Number of public subnets")
    private_subnets: int = Field(default=0, ge=0, le=6, description="Number of private subnets")

    # --- Compute ---
    ec2_instances: int = Field(default=0, ge=0, le=20, description="Number of EC2 instances")
    instance_type: str = Field(default="t3.micro", description="EC2 instance type")

    # --- Scaling & traffic ---
    autoscaling: bool = Field(default=False, description="Enable Auto Scaling Group")
    load_balancer: bool = Field(default=False, description="Create an Application Load Balancer")

    # --- Database ---
    database: bool = Field(default=False, description="Create an RDS instance")
    db_engine: str = Field(default="mysql", description="RDS engine: mysql | postgres")
    db_private: bool = Field(default=True, description="Place RDS in private subnet")

    # --- Connectivity ---
    nat_gateway: bool = Field(default=False, description="Create NAT Gateway for private subnets")

    # --- Cost ---
    cost_optimized: bool = Field(default=False, description="Apply cost-saving defaults")

    @model_validator(mode="after")
    def enforce_dependencies(self) -> "InfrastructureSchema":
        # Any subnet or instance needs a VPC
        if (self.public_subnets > 0 or self.private_subnets > 0 or
                self.ec2_instances > 0) and not self.vpc:
            self.vpc = True

        # Instances need at least one public subnet
        if self.ec2_instances > 0 and self.public_subnets == 0:
            self.public_subnets = 1

        # Private subnets need a NAT gateway for outbound internet
        if self.private_subnets > 0 and not self.nat_gateway:
            self.nat_gateway = True

        # Database must go in a private subnet
        if self.database and self.private_subnets == 0:
            self.private_subnets = 2

        # Load balancer needs at least 2 public subnets (multi-AZ)
        if self.load_balancer and self.public_subnets < 2:
            self.public_subnets = 2

        # Cost optimized overrides
        if self.cost_optimized:
            self.instance_type = "t3.micro"
            if self.nat_gateway and self.private_subnets == 0:
                self.nat_gateway = False

        return self


class PlannerResponse(BaseModel):
    ok: bool
    architecture: Optional[InfrastructureSchema] = None
    error: Optional[str] = None


class GenerateResponse(BaseModel):
    architecture: dict
    warnings: List[str]
    optimizations: List[str]
    terraform: str