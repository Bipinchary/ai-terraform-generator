from jinja2 import Environment, FileSystemLoader
import os

# Gets the directory where terraform_generator.py is located
current_dir = os.path.dirname(os.path.abspath(__file__))
# Points to the templates folder relative to this file
template_path = os.path.join(current_dir, "..", "templates")
env = Environment(loader=FileSystemLoader(template_path))

def generate_terraform(architecture):

    terraform_code = ""

    if architecture.get("vpc"):
        template = env.get_template("vpc.tf.j2")
        terraform_code += template.render(cidr_block="10.0.0.0/16")

    for i in range(architecture.get("subnets", 0)):
        template = env.get_template("subnet.tf.j2")
        terraform_code += template.render(index=i+1, cidr=f"10.0.{i+1}.0/24")

    for i in range(architecture.get("ec2_instances", 0)):
        template = env.get_template("ec2.tf.j2")
        terraform_code += template.render(index=i+1)

    os.makedirs("terraform-output", exist_ok=True)

    with open("terraform-output/main.tf", "w") as f:
        f.write(terraform_code)

    return terraform_code