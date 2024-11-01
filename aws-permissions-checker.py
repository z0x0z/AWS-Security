

"""
Usage: 
aws iam get-account-authorization-details --profile tazapay > gaad.json
Mention the above json file in line 20 below..

"""

import json
import csv
from rich.console import Console
from rich.table import Table
from rich.align import Align

# Initialize a console for Rich output
console = Console()

# Load the JSON file
with open('gaad.json') as f:
    data = json.load(f)

# Define permissions to search for
exact_permissions = {"secretsmanager:GetSecretValue", "secretsmanager:*"}
prefix_permissions = {}  # Only include prefixes if desired

"""
Example Usage 
exact_permissions = {"iam:*", "secretsmanager:GetSecretValue"}
prefix_permissions = {"secretsmanager:","s3:"}

"""

# Initialize a set to store unique rows for the main table output
unique_entries = set()
# Initialize a set to track groups that appear in the main permissions table
groups_with_permissions = set()
# Dictionary to store group-to-user mappings for users in groups with matching permissions
group_user_mapping = {}

# Function to check if an action matches exact or prefix permissions, including full access (*)
def matches_permission(action):
    # Check if action is an exact match, matches a prefix, or is "*"
    if action in exact_permissions or action == "*":
        return True
    if prefix_permissions:
        return any(action.startswith(prefix.rstrip("*")) for prefix in prefix_permissions)
    return False

# Process user groups and check their permissions
for group in data.get("GroupDetailList", []):
    group_name = group.get("GroupName")
    inline_policies = group.get("GroupPolicyList", [])
    managed_policies = group.get("AttachedManagedPolicies", [])

    # Initialize an empty list for each group in the mapping
    group_user_mapping[group_name] = []

    # Check inline policies for groups
    for policy in inline_policies:
        policy_name = policy.get("PolicyName")
        policy_doc = policy.get("PolicyDocument", {}).get("Statement", [])
        
        for statement in policy_doc:
            actions = statement.get("Action", [])
            if isinstance(actions, str):
                actions = [actions]
            matched_actions = [action for action in actions if matches_permission(action)]
            
            if matched_actions:
                groups_with_permissions.add(group_name)  # Track this group as it has matching permissions
                for action in matched_actions:
                    unique_entries.add((group_name, policy_name, "group", "inline", action))

    # Check managed policies for groups
    for policy in managed_policies:
        policy_arn = policy.get("PolicyArn")
        
        for managed_policy in data.get("Policies", []):
            if managed_policy.get("Arn") == policy_arn:
                policy_name = managed_policy.get("PolicyName")
                policy_doc = managed_policy.get("PolicyVersionList", [])[0].get("Document", {}).get("Statement", [])
                
                for statement in policy_doc:
                    actions = statement.get("Action", [])
                    if isinstance(actions, str):
                        actions = [actions]
                    matched_actions = [action for action in actions if matches_permission(action)]
                    
                    if matched_actions:
                        groups_with_permissions.add(group_name)  # Track this group as it has matching permissions
                        for action in matched_actions:
                            unique_entries.add((group_name, policy_name, "group", "managed", action))

# Map users to their respective groups with permissions
for user in data.get("UserDetailList", []):
    user_name = user.get("UserName")
    groups = user.get("GroupList", [])  # Groups this user belongs to
    
    for group in groups:
        if group in group_user_mapping:
            group_user_mapping[group].append(user_name)  # Add user to the group if it has matching permissions

# Process individual IAM users
for user in data.get("UserDetailList", []):
    user_name = user.get("UserName")
    inline_policies = user.get("UserPolicyList", [])
    managed_policies = user.get("AttachedManagedPolicies", [])

    # Process inline policies for users
    for policy in inline_policies:
        policy_name = policy.get("PolicyName")
        policy_doc = policy.get("PolicyDocument", {}).get("Statement", [])
        
        for statement in policy_doc:
            actions = statement.get("Action", [])
            if isinstance(actions, str):
                actions = [actions]
            matched_actions = [action for action in actions if matches_permission(action)]
            
            if matched_actions:
                for action in matched_actions:
                    unique_entries.add((user_name, policy_name, "user", "inline", action))

    # Process managed policies for users
    for policy in managed_policies:
        policy_arn = policy.get("PolicyArn")
        
        for managed_policy in data.get("Policies", []):
            if managed_policy.get("Arn") == policy_arn:
                policy_name = managed_policy.get("PolicyName")
                policy_doc = managed_policy.get("PolicyVersionList", [])[0].get("Document", {}).get("Statement", [])
                
                for statement in policy_doc:
                    actions = statement.get("Action", [])
                    if isinstance(actions, str):
                        actions = [actions]
                    matched_actions = [action for action in actions if matches_permission(action)]
                    
                    if matched_actions:
                        for action in matched_actions:
                            unique_entries.add((user_name, policy_name, "user", "managed", action))

# Process individual IAM roles
for role in data.get("RoleDetailList", []):
    role_name = role.get("RoleName")
    inline_policies = role.get("RolePolicyList", [])
    managed_policies = role.get("AttachedManagedPolicies", [])

    # Process inline policies for roles
    for policy in inline_policies:
        policy_name = policy.get("PolicyName")
        policy_doc = policy.get("PolicyDocument", {}).get("Statement", [])
        
        for statement in policy_doc:
            actions = statement.get("Action", [])
            if isinstance(actions, str):
                actions = [actions]
            matched_actions = [action for action in actions if matches_permission(action)]
            
            if matched_actions:
                for action in matched_actions:
                    unique_entries.add((role_name, policy_name, "role", "inline", action))

    # Process managed policies for roles
    for policy in managed_policies:
        policy_arn = policy.get("PolicyArn")
        
        for managed_policy in data.get("Policies", []):
            if managed_policy.get("Arn") == policy_arn:
                policy_name = managed_policy.get("PolicyName")
                policy_doc = managed_policy.get("PolicyVersionList", [])[0].get("Document", {}).get("Statement", [])
                
                for statement in policy_doc:
                    actions = statement.get("Action", [])
                    if isinstance(actions, str):
                        actions = [actions]
                    matched_actions = [action for action in actions if matches_permission(action)]
                    
                    if matched_actions:
                        for action in matched_actions:
                            unique_entries.add((role_name, policy_name, "role", "managed", action))

# Convert the set to a list for tabulation
table_data = list(unique_entries)

# Sort by Resource Type (users first, then groups, then roles)
sort_order = {"user": 1, "group": 2, "role": 3}
table_data.sort(key=lambda x: (sort_order.get(x[2], 4), x[0]))

#print('##### Welcome to the AWS Permissions Checker by z0x0z #####')

# Display the main permissions table with Rich and left-aligned title
main_table = Table(show_header=True, header_style="bold #00FFFF", title="\n##### Welcome to the AWS Permissions Checker by Gopikrishna #####\n##### Permissions Table Sorted by Resource Type #####", title_justify="center", title_style="bold #6a5acd")

# Adding center-aligned headers, but setting row justification to left
main_table.add_column(Align("Principle", align="center"), justify="left")
main_table.add_column(Align("Policy Name", align="center"), justify="left")
main_table.add_column(Align("Resource Type", align="center"), justify="left")
main_table.add_column(Align("Policy Type", align="center"), justify="left")
main_table.add_column(Align("Permission", align="center"), justify="left")

for row in table_data:
    main_table.add_row(*map(str, row))

console.print(main_table)

# Display tables for each group showing group members, only if the group exists in the main permissions table
print('\n\nOnly the groups which has IAM Users attached to it are displayed.. Groups without IAM Users (Empty Groups) are not displayed\n')
for group_name, users in group_user_mapping.items():
    if group_name in groups_with_permissions and users:  # Display only if group exists in main table
        user_table = Table(show_header=True, header_style="bold #ff69b4")
        user_table.add_column(Align(f"Users in '{group_name}' Group", align="center"), justify="left")

        for user in users:
            user_table.add_row(user)

        console.print(user_table)

# Option to save as CSV
export_to_csv = input("Would you like to export the output to a CSV file? (yes/no): ").strip().lower()
if export_to_csv == "yes":
    with open("permissions_output.csv", mode="w", newline="") as file:
        writer = csv.writer(file)
        
        # Write main permissions table
        writer.writerow(["Main Permissions Table"])
        writer.writerow(["Name", "Policy Name", "Resource Type", "Policy Type", "Permission"])
        writer.writerows(table_data)
        
        # Write users in group tables
        for group_name, users in group_user_mapping.items():
            if group_name in groups_with_permissions and users:
                writer.writerow([])  # Blank line separator
                writer.writerow([f"Users in Group '{group_name}' Table"])
                writer.writerow(["User"])
                for user in users:
                    writer.writerow([user])
    
    print("Output saved to 'permissions_output.csv'")
