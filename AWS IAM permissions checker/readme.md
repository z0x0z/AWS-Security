## AWS IAM Permissions Checker

### Description

This script is to find "Which permissions are assigned to Whom in an AWS account".  
The script processes AWS IAM permissions data to generate two main tables:

1. **The Main Permissions Table** detailing users, groups, roles and their associated permissions.
1. **Users in Group Table** for each IAM group with matching permissions, listing the users within that group.  

The script outputs the tables in the console using rich formatting and provides an option to export both tables into a single CSV file.

### Usage

#### Prerequisites
- Python 3.x
- `rich` library for displaying output as table  
  ```
  pip install rich
  ```

#### Running the Script

1. **Prepare the Input File**:
	- Configure the AWS CLI with credentials to perform gaad analysis using the following command
	``` aws iam get-account-authorization-details --profile Chuma > gaad.json ```

2. **Execute the Script**:
	- Enter the name of the above json file inside the script in line number 18
	- Mention the permissions to look for inside the script in line number 24
		> Example  
		> exact_permissions = {"iam:*", "secretsmanager:GetSecretValue"}    
		> prefix_permissions = {"secretsmanager:","s3:"}


   - Run the script in the terminal  
     ```
     python aws-iam-permissions-checker.py
     ```

1. **Export to CSV**:
   - When prompted with `Would you like to export the output to a CSV file? (yes/no):`, enter `yes` to save the output to a CSV file.
   - The output will be saved to `aws_iam.csv` in the same directory.
	- The output CSV file, named aws_iam.csv, will contain the Main Permissions Table followed by each Users in Group Table. Each group table is separated by a blank line for clarity.

![](sc.png)