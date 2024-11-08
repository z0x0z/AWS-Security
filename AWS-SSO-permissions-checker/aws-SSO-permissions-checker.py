import boto3
import csv
import argparse
from rich.console import Console
from rich.table import Table
from rich.align import Align

# Initialize console for Rich output
console = Console()

# Parse command-line arguments
parser = argparse.ArgumentParser(description="AWS Identity Center Data Fetcher")
parser.add_argument("--profile", type=str, help="AWS CLI profile name", default=None)
parser.add_argument("--region", type=str, help="AWS region", default=None)
args = parser.parse_args()

# Create a session based on profile and region options
if args.profile and args.region:
    session = boto3.Session(profile_name=args.profile, region_name=args.region)
elif args.profile:
    session = boto3.Session(profile_name=args.profile)
elif args.region:
    session = boto3.Session(region_name=args.region)
else:
    session = boto3.Session()

# Initialize AWS clients with the session
sso_admin_client = session.client('sso-admin')
identity_store_client = session.client('identitystore')

# Set up the instance and identity store IDs
INSTANCE_ARN = "arn:aws:sso:::instance/ssoins-7223da93bb899906"
IDENTITY_STORE_ID = "d-9067b222fc"

# Fetch available accounts and permission sets with pagination
def get_available_accounts():
    accounts = []
    permission_sets = []

    paginator = sso_admin_client.get_paginator('list_permission_sets')
    for page in paginator.paginate(InstanceArn=INSTANCE_ARN):
        permission_sets.extend(page['PermissionSets'])

    for permission_set_arn in permission_sets:
        account_ids = sso_admin_client.list_accounts_for_provisioned_permission_set(
            InstanceArn=INSTANCE_ARN,
            PermissionSetArn=permission_set_arn
        )['AccountIds']

        for account_id in account_ids:
            if account_id not in [acc["ID"] for acc in accounts]:  # Avoid duplicates
                account_name = session.client("organizations").describe_account(AccountId=account_id)['Account']['Name']
                accounts.append({"ID": account_id, "Name": account_name})

    return accounts, permission_sets

# Fetch data for permission sets across all accounts (Script 1 functionality)
def fetch_permission_set_data_all(permission_sets):
    assignments_data = []
    policies_data = []

    for permission_set_arn in permission_sets:
        permission_set_name = sso_admin_client.describe_permission_set(
            InstanceArn=INSTANCE_ARN,
            PermissionSetArn=permission_set_arn
        )['PermissionSet']['Name']

        aws_managed_policies_response = sso_admin_client.list_managed_policies_in_permission_set(
            InstanceArn=INSTANCE_ARN,
            PermissionSetArn=permission_set_arn
        )
        aws_managed_policies = [policy['Name'] for policy in aws_managed_policies_response.get('AttachedManagedPolicies', [])]

        customer_managed_policies_response = sso_admin_client.list_customer_managed_policy_references_in_permission_set(
            InstanceArn=INSTANCE_ARN,
            PermissionSetArn=permission_set_arn
        )
        customer_managed_policies = [policy['Name'] for policy in customer_managed_policies_response.get('CustomerManagedPolicyReferences', [])]

        inline_policy_response = sso_admin_client.get_inline_policy_for_permission_set(
            InstanceArn=INSTANCE_ARN,
            PermissionSetArn=permission_set_arn
        )
        inline_policy = inline_policy_response.get('InlinePolicy', "None")

        account_ids = sso_admin_client.list_accounts_for_provisioned_permission_set(
            InstanceArn=INSTANCE_ARN,
            PermissionSetArn=permission_set_arn
        )['AccountIds']

        for account_id in account_ids:
            assignments = sso_admin_client.list_account_assignments(
                InstanceArn=INSTANCE_ARN,
                AccountId=account_id,
                PermissionSetArn=permission_set_arn
            )['AccountAssignments']

            for assignment in assignments:
                principal_type = assignment['PrincipalType']
                principal_id = assignment['PrincipalId']
                principal_name = None

                if principal_type == "USER":
                    principal_name = identity_store_client.describe_user(
                        IdentityStoreId=IDENTITY_STORE_ID,
                        UserId=principal_id
                    )['UserName']
                elif principal_type == "GROUP":
                    principal_name = identity_store_client.describe_group(
                        IdentityStoreId=IDENTITY_STORE_ID,
                        GroupId=principal_id
                    )['DisplayName']

                assignments_data.append({
                    "Type": principal_type,
                    "Name": principal_name,
                    "Permission Set": permission_set_name,
                    "Account ID": account_id
                })

        policies_data.append({
            "Permission Set": permission_set_name,
            "AWS Managed Policies": aws_managed_policies if aws_managed_policies else ["None"],
            "Customer Managed Policies": customer_managed_policies if customer_managed_policies else ["None"],
            "Inline Policy": inline_policy if inline_policy else "None"
        })

    assignments_data = sorted(assignments_data, key=lambda x: (x["Type"] != "USER", x["Type"]))
    return assignments_data, policies_data

# Fetch data for permission sets for a specific account (Script 2 functionality)
def fetch_permission_set_data(account_id, permission_sets):
    assignments_data = []
    policies_data = []
    assigned_permission_sets = set()  # Track permission sets assigned to the selected account

    for permission_set_arn in permission_sets:
        permission_set_name = sso_admin_client.describe_permission_set(
            InstanceArn=INSTANCE_ARN,
            PermissionSetArn=permission_set_arn
        )['PermissionSet']['Name']

        assignments = sso_admin_client.list_account_assignments(
            InstanceArn=INSTANCE_ARN,
            AccountId=account_id,
            PermissionSetArn=permission_set_arn
        )['AccountAssignments']

        if assignments:
            assigned_permission_sets.add(permission_set_arn)
            for assignment in assignments:
                principal_type = assignment['PrincipalType']
                principal_id = assignment['PrincipalId']
                principal_name = None

                if principal_type == "USER":
                    principal_name = identity_store_client.describe_user(
                        IdentityStoreId=IDENTITY_STORE_ID,
                        UserId=principal_id
                    )['UserName']
                elif principal_type == "GROUP":
                    principal_name = identity_store_client.describe_group(
                        IdentityStoreId=IDENTITY_STORE_ID,
                        GroupId=principal_id
                    )['DisplayName']

                assignments_data.append({
                    "Type": principal_type,
                    "Name": principal_name,
                    "Permission Set": permission_set_name,
                    "Account ID": account_id
                })

        if permission_set_arn in assigned_permission_sets:
            aws_managed_policies_response = sso_admin_client.list_managed_policies_in_permission_set(
                InstanceArn=INSTANCE_ARN,
                PermissionSetArn=permission_set_arn
            )
            aws_managed_policies = [policy['Name'] for policy in aws_managed_policies_response.get('AttachedManagedPolicies', [])]

            customer_managed_policies_response = sso_admin_client.list_customer_managed_policy_references_in_permission_set(
                InstanceArn=INSTANCE_ARN,
                PermissionSetArn=permission_set_arn
            )
            customer_managed_policies = [policy['Name'] for policy in customer_managed_policies_response.get('CustomerManagedPolicyReferences', [])]

            inline_policy_response = sso_admin_client.get_inline_policy_for_permission_set(
                InstanceArn=INSTANCE_ARN,
                PermissionSetArn=permission_set_arn
            )
            inline_policy = inline_policy_response.get('InlinePolicy', "None")

            policies_data.append({
                "Permission Set": permission_set_name,
                "AWS Managed Policies": aws_managed_policies if aws_managed_policies else ["None"],
                "Customer Managed Policies": customer_managed_policies if customer_managed_policies else ["None"],
                "Inline Policy": inline_policy if inline_policy else "None"
            })

    return assignments_data, policies_data

# Display tables with assignment data and policies
def display_tables(assignments_data, policies_data, user_group_map):
    # Assignments table
    assignment_table = Table(title="Assignments", show_header=True, header_style="bold white",title_style="bold #ab79d5")
    assignment_table.add_column(Align("Type",align="center"), style="white", justify="center")
    assignment_table.add_column(Align("User/Group Name",align="center"), style="green", justify="left")
    assignment_table.add_column(Align("Permission Set",align="center"), style="yellow", justify="left")
    assignment_table.add_column(Align("Account ID",align="center"), style="blue", justify="left")

    for assignment in assignments_data:
        assignment_table.add_row(
            assignment["Type"],
            assignment["Name"],
            assignment["Permission Set"],
            assignment["Account ID"]
        )
    console.print(assignment_table)

    # Policies table
    policy_table = Table(title="Policies Attached to Permission Sets", header_style="bold white",title_style="bold #ab79d5")
    policy_table.add_column(Align("Permission Set",align="center"), style="white", justify="left")
    policy_table.add_column(Align("AWS Managed Policies",align="center"), style="green", justify="left")
    policy_table.add_column(Align("Customer Managed Policies",align="center"), style="yellow", justify="left")
    policy_table.add_column(Align("Inline Policy",align="center"), style="blue", justify="left")

    for policy in policies_data:
        policy_table.add_row(
            policy["Permission Set"],
            "\n".join(policy["AWS Managed Policies"]),
            "\n".join(policy["Customer Managed Policies"]),
            policy["Inline Policy"]
        )
    console.print("\n",policy_table)

    # User-Group Memberships table
    user_group_table = Table(title="User-Group Memberships", header_style="bold white",title_style="bold #ab79d5")
    user_group_table.add_column(Align("User Name",align="center"), style="white", justify="left")
    user_group_table.add_column(Align("Groups",align="center"), style="green", justify="left")

    for user_name, groups in user_group_map.items():
        user_group_table.add_row(user_name, ", ".join(groups))
    console.print("\n",user_group_table)

# Fetch user-group memberships based on assignments
def fetch_user_group_memberships(assignments_data=None):
    user_group_map = {}
    assigned_groups = {assignment["Name"] for assignment in assignments_data if assignment["Type"] == "GROUP"} if assignments_data else None

    for group in identity_store_client.list_groups(IdentityStoreId=IDENTITY_STORE_ID)['Groups']:
        group_id = group['GroupId']
        group_name = group['DisplayName']
        
        if assigned_groups and group_name not in assigned_groups:
            continue

        members_response = identity_store_client.list_group_memberships(
            IdentityStoreId=IDENTITY_STORE_ID,
            GroupId=group_id
        )['GroupMemberships']

        for member in members_response:
            user_id = member['MemberId']['UserId']
            user_name = identity_store_client.describe_user(
                IdentityStoreId=IDENTITY_STORE_ID,
                UserId=user_id
            )['UserName']
            
            if user_name not in user_group_map:
                user_group_map[user_name] = []
            user_group_map[user_name].append(group_name)

    return user_group_map

# Export data to CSV with proper formatting for multiple policies and user-group mappings
def export_to_csv(assignments_data, policies_data, user_group_map, filename="aws_sso.csv"):
    with open(filename, mode="w", newline="") as file:
        writer = csv.writer(file)
        
        # Write assignment data
        writer.writerow(["Type", "User/Group Name", "Permission Set", "Account ID"])
        for assignment in assignments_data:
            writer.writerow([assignment["Type"], assignment["Name"], assignment["Permission Set"], assignment["Account ID"]])
        
        writer.writerow([])  # Blank row to separate tables

        # Write policies data
        writer.writerow(["Permission Set", "AWS Managed Policies", "Customer Managed Policies", "Inline Policy"])
        for policy in policies_data:
            max_rows = max(len(policy["AWS Managed Policies"]), len(policy["Customer Managed Policies"]), 1)
            for i in range(max_rows):
                aws_policy = policy["AWS Managed Policies"][i] if i < len(policy["AWS Managed Policies"]) else ""
                customer_policy = policy["Customer Managed Policies"][i] if i < len(policy["Customer Managed Policies"]) else ""
                inline = policy["Inline Policy"] if i == 0 else ""
                writer.writerow([policy["Permission Set"] if i == 0 else "", aws_policy, customer_policy, inline])

        writer.writerow([])  # Blank row to separate tables

        # Write user-group membership data
        writer.writerow(["User Name", "Groups"])
        for user_name, groups in user_group_map.items():
            writer.writerow([user_name, ", ".join(groups)])

    console.print(f"Data exported to {filename}")

# Main flow
if __name__ == "__main__":
    console.print("\n[bold cyan]-------- AWS Identity Center Permissions Checker created by Gopikrishna --------[/bold cyan]\n", justify="center")

    # Prompt for choice to enumerate all accounts or a specific account
    choice = console.input("Type 'yes' to enumerate all accounts, or 'no' to enumerate a specific account: ").strip().lower()
    console.print("Fetching data... Please wait.\n")

    accounts, permission_sets = get_available_accounts()

    if choice == 'yes':
        console.print("[bold white]Available Accounts:[/bold white]")
        for idx, account in enumerate(accounts, start=1):
            console.print(f"{idx}. {account['Name']} (ID: {account['ID']})")
        console.print("\n")
        assignments_data, policies_data = fetch_permission_set_data_all(permission_sets)
        user_group_map = fetch_user_group_memberships()
    else:
        # Display accounts and select a specific account
        console.print("[bold white]Available Accounts:[/bold white]")
        for idx, account in enumerate(accounts, start=1):
            console.print(f"{idx}. {account['Name']} (ID: {account['ID']})")
        selected_index = int(console.input("\nEnter the number of the account for which you want details: ").strip()) - 1
        console.print("Fetching data... Please wait.\n")
        selected_account_id = accounts[selected_index]["ID"]

        assignments_data, policies_data = fetch_permission_set_data(selected_account_id, permission_sets)
        user_group_map = fetch_user_group_memberships(assignments_data)

    # Display tables
    display_tables(assignments_data, policies_data, user_group_map)

    # Prompt for CSV export
    export_choice = console.input("Would you like to export the data to CSV? (yes/no): ").strip().lower()
    if export_choice == "yes":
        export_filename = console.input("Enter filename for CSV (default: aws_sso.csv): ").strip() or "aws_sso.csv"
        export_to_csv(assignments_data, policies_data, user_group_map, export_filename)
