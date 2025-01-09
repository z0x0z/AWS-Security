import boto3
from botocore.exceptions import ClientError
from rich.table import Table
from rich.console import Console
import argparse

# Initialize the Rich console
console = Console()

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Manage CloudFormation stack termination protection')
    parser.add_argument('--profile', 
                       type=str,
                       help='AWS profile name to use',
                       default='default')
    return parser.parse_args()

def get_active_stacks(region, profile_name):
    """Retrieve the names of active CloudFormation stacks in a specific region."""
    try:
        session = boto3.Session(profile_name=profile_name)
        cf_client = session.client("cloudformation", region_name=region)
        response = cf_client.list_stacks(
            StackStatusFilter=[
                "CREATE_COMPLETE", "UPDATE_COMPLETE", "ROLLBACK_COMPLETE"
            ]
        )
        active_stacks = response.get("StackSummaries", [])
        return active_stacks
    except ClientError as e:
        console.print(f"[bold red]Error fetching stack names for region {region}: {e}[/bold red]")
        return []

def get_termination_protection_status(stack_name, region, profile_name):
    """Check whether termination protection is enabled for a stack."""
    try:
        session = boto3.Session(profile_name=profile_name)
        cf_client = session.client("cloudformation", region_name=region)
        response = cf_client.describe_stacks(StackName=stack_name)
        termination_protection = response['Stacks'][0].get('EnableTerminationProtection', False)
        return termination_protection
    except ClientError as e:
        console.print(f"[bold red]Error checking termination protection for stack {stack_name} in region {region}: {e}[/bold red]")
        return False

def enable_termination_protection(stack_name, region, profile_name):
    """Enable termination protection for a given stack in a specific region."""
    try:
        session = boto3.Session(profile_name=profile_name)
        cf_client = session.client("cloudformation", region_name=region)
        cf_client.update_termination_protection(
            StackName=stack_name,
            EnableTerminationProtection=True
        )
        return True, f"Termination protection enabled for stack: {stack_name} in region {region}"
    except ClientError as e:
        return False, f"Failed to enable termination protection for stack: {stack_name} in region {region}. Error: {e}"

def get_all_regions(profile_name):
    """Get a list of all AWS regions."""
    session = boto3.Session(profile_name=profile_name)
    ec2_client = session.client('ec2')
    response = ec2_client.describe_regions()
    return [region['RegionName'] for region in response['Regions']]

def main():
    """Main function to manage termination protection for active stacks in all regions."""
    # Parse command line arguments
    args = parse_arguments()
    profile_name = args.profile

    # Print which profile is being used
    console.print(f"[bold blue]Using AWS profile: {profile_name}[/bold blue]")

    regions = get_all_regions(profile_name)
    if not regions:
        console.print("[bold red]No regions found! Exiting...[/bold red]")
        return

    # Create a Rich table for the output
    table = Table(title="CloudFormation Active Stacks and Termination Protection Status")
    table.add_column("Region", style="cyan", no_wrap=True)
    table.add_column("Stack Name", style="cyan", no_wrap=True)
    table.add_column("Status", style="green", justify="center")
    table.add_column("Termination Protection", justify="center", style="yellow")
    table.add_column("Reason (if not enabled)", style="white")

    # Process each region
    stacks_info = []
    for region in regions:
        active_stacks = get_active_stacks(region, profile_name)
        if not active_stacks:
            continue

        for stack in active_stacks:
            stack_name = stack["StackName"]
            status = stack["StackStatus"]
            termination_protection = get_termination_protection_status(stack_name, region, profile_name)
            if termination_protection:
                protection_status = "Enabled"
                reason = ""
            else:
                protection_status = "Disabled"
                reason = "Termination protection is not enabled."

            stacks_info.append({
                "region": region,
                "stack_name": stack_name,
                "status": status,
                "protection_status": protection_status,
                "reason": reason
            })

    # Display the table with active stacks
    for info in stacks_info:
        table.add_row(
            info['region'], 
            info['stack_name'], 
            info['status'], 
            info['protection_status'], 
            info['reason']
        )

    console.print(table)

    # Ask for user input whether to proceed with enabling termination protection
    proceed = console.input("[bold cyan]Do you want to enable termination protection for these stacks? (yes/no): [/bold cyan]").strip().lower()

    if proceed == "yes":
        # Enable termination protection for each stack
        result_table = Table(title="Termination Protection Status After Update")
        result_table.add_column("Region", style="cyan", no_wrap=True)
        result_table.add_column("Stack Name", style="cyan", no_wrap=True)
        result_table.add_column("Status", justify="center", style="green")
        result_table.add_column("Termination Protection", justify="center", style="yellow")
        result_table.add_column("Message", style="white")

        for info in stacks_info:
            stack_name = info['stack_name']
            region = info['region']
            success, message = enable_termination_protection(stack_name, region, profile_name)
            status = "Success" if success else "Failed"
            protection_status = "Enabled" if success else "Not Enabled"
            result_table.add_row(region, stack_name, status, protection_status, message)

        # Display the result table after the update
        console.print(result_table)
    else:
        console.print("[bold red]Exiting without making changes...[/bold red]")

if __name__ == "__main__":
    main()
