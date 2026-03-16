# run_test.py
from backend.generator.terraform_generator import generate_terraform

# STEP 5: Define the Architecture JSON
architecture = {
    "vpc": True,
    "subnets": 2,
    "ec2_instances": 1
}

if __name__ == "__main__":
    print("🚀 Starting Terraform Generation...")
    
    # Run the generator function
    code = generate_terraform(architecture)
    
    print("✅ Generation Complete!")
    print(f"📂 File created at: terraform-output/main.tf")
    print("\n--- Preview of generated code ---")
    print(code)