import boto3
import sys
from rich.table import Table
from rich.console import Console


# Function to fetch unique SGs with open inbound rules to 0.0.0.0/0
def fetch_sg_with_open_inbound(ec2):
    response = ec2.describe_security_groups()

    open_sgs = set()  # Use a set to ensure unique SG IDs
    for sg in response["SecurityGroups"]:
        for permission in sg.get("IpPermissions", []):
            for ip_range in permission.get("IpRanges", []):
                if ip_range.get("CidrIp") == "0.0.0.0/0":
                    open_sgs.add(sg["GroupId"])  # Add SG ID to the set
                    break
    return list(open_sgs)  # Convert set back to a list for further processing


# Function to check service associations
def check_service_associations(sg_id, service, function, description):
    try:
        result = function(sg_id)
        if result:
            return {
                "Service": service,
                "Description": description,
                "Result": ", ".join(result)
            }
        else:
            return None  # Skip services with no associations
    except Exception as e:
        return {
            "Service": service,
            "Description": description,
            "Result": f"Error: {str(e)}"
        }


# Functions to query AWS resources
def check_rds(sg_id, session):
    client = session.client("rds")
    response = client.describe_db_instances()
    return [db["DBInstanceIdentifier"] for db in response["DBInstances"]
            if sg_id in [sg["VpcSecurityGroupId"] for sg in db["VpcSecurityGroups"]]]


def check_ec2(sg_id, session):
    client = session.client("ec2")
    response = client.describe_instances(Filters=[{"Name": "instance.group-id", "Values": [sg_id]}])
    return [instance["InstanceId"] for reservation in response["Reservations"] for instance in reservation["Instances"]]


def check_elb(sg_id, session):
    client = session.client("elb")
    response = client.describe_load_balancers()
    return [lb["LoadBalancerName"] for lb in response["LoadBalancerDescriptions"] if sg_id in lb["SecurityGroups"]]


def check_vpc(sg_id, session):
    client = session.client("ec2")
    response = client.describe_security_groups(GroupIds=[sg_id])
    return [sg["VpcId"] for sg in response["SecurityGroups"]]


def check_eks(sg_id, session):
    client = session.client("eks")
    response = client.list_clusters()
    clusters = response["clusters"]
    matched_clusters = []
    for cluster_name in clusters:
        cluster = client.describe_cluster(name=cluster_name)
        if sg_id in cluster["cluster"]["resourcesVpcConfig"]["securityGroupIds"]:
            matched_clusters.append(cluster_name)
    return matched_clusters


def check_redis(sg_id, session):
    client = session.client("elasticache")
    response = client.describe_cache_clusters()
    return [cache["CacheClusterId"] for cache in response["CacheClusters"]
            if sg_id in [sg["SecurityGroupId"] for sg in cache.get("SecurityGroups", [])]]


def check_memorydb(sg_id, session):
    client = session.client("memorydb")
    response = client.describe_clusters()
    return [cluster["Name"] for cluster in response["Clusters"]
            if sg_id in [sg["SecurityGroupId"] for sg in cluster.get("SecurityGroups", [])]]


def check_ecs(sg_id, session):
    client = session.client("ecs")
    response = client.list_clusters()
    clusters = response["clusterArns"]
    matched_tasks = []
    for cluster_arn in clusters:
        tasks = client.list_tasks(cluster=cluster_arn)
        if not tasks["taskArns"]:
            continue
        task_descriptions = client.describe_tasks(cluster=cluster_arn, tasks=tasks["taskArns"])
        for task in task_descriptions["tasks"]:
            for attachment in task.get("attachments", []):
                for detail in attachment.get("details", []):
                    if detail.get("value") == sg_id:
                        matched_tasks.append(task["taskArn"])
    return matched_tasks


# Main function
def main():
    # Ask user for AWS profile
    aws_profile = input("Enter the AWS profile to use (press Enter to use 'default'): ").strip() or "default"

    # Set up session with the chosen profile
    session = boto3.Session(profile_name=aws_profile)
    ec2 = session.client("ec2")

    # Fetch unique SGs with open inbound rules
    print("Fetching Security Groups with inbound rules open to 0.0.0.0/0...")
    sg_ids = fetch_sg_with_open_inbound(ec2)

    if not sg_ids:
        print("No Security Groups found with inbound rules open to 0.0.0.0/0.")
        sys.exit(0)

    print(f"Found {len(sg_ids)} Security Groups with open inbound rules:")
    for sg_id in sg_ids:
        print(f"- {sg_id}")

    # Table to display results
    console = Console()
    table = Table(title="Security Group Associations")
    table.add_column("SG ID", justify="center", style="bold")
    table.add_column("Service", justify="center")
    table.add_column("Description", justify="center")
    table.add_column("Result", justify="left")

    # Service checks
    service_checks = [
        ("RDS", check_rds, "Relational Database Service (RDS)"),
        ("ECS", check_ecs, "Elastic Container Service (ECS)"),
        ("EKS", check_eks, "Elastic Kubernetes Service (EKS)"),
        ("EC2", check_ec2, "Elastic Compute Cloud (EC2)"),
        ("ELB", check_elb, "Elastic Load Balancing (ELB)"),
        ("VPC", check_vpc, "Virtual Private Cloud (VPC)"),
        ("ElastiCache", check_redis, "ElastiCache"),
        ("MemoryDB", check_memorydb, "MemoryDB"),
    ]

    # Process each SG ID
    for sg_id in sg_ids:
        print(f"\nChecking associations for Security Group: {sg_id}...")

        for service, function, description in service_checks:
            result = check_service_associations(sg_id, service, lambda sg_id: function(sg_id, session), description)
            if result:  # Add only if there's an association
                table.add_row(sg_id, result["Service"], result["Description"], result["Result"])

    # Display the table if it has rows
    if len(table.rows) > 0:
        console.print(table)
    else:
        print("No associations found for any Security Group.")


if __name__ == "__main__":
    main()

