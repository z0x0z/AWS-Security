# AWS-Security

Welcome to the **z0x0z-AWS-Security** repository! This repository contains a collection of Python scripts and tools designed to enhance the security of your AWS environment by providing checks and reports on common security configurations. Each subdirectory focuses on a specific AWS security area, with detailed scripts and instructions.


## Tools Included

### 1. **AWS Security Group Internet Exposure Checker**
- **Script**: `AWS_sg_internet_exposure_checker.py`
- **Description**: Scans AWS Security Groups to identify rules that expose resources to the internet.
- **Location**: `AWS Security Group Internet Exposure Checker/`
- **Readme**: Detailed instructions can be found in `AWS Security Group Internet Exposure Checker/readme.md`.

### 2. **AWS IAM Permissions Checker**
- **Script**: `aws-iam-permissions-checker.py`
- **Description**: Analyzes AWS IAM permissions to detect misconfigurations or overly permissive policies.
- **Location**: `AWS IAM permissions checker/`
- **Readme**: Documentation is available in `AWS IAM permissions checker/readme.md`.

### 3. **AWS SSO Permissions Checker**
- **Script**: `aws-SSO-permissions-checker.py`
- **Description**: Checks AWS SSO permissions for potential misconfigurations or compliance issues.
- **Location**: `AWS SSO permissions checker/`
- **Readme**: Details are provided in `AWS SSO permissions checker/readme.md`.

### 4. **AWS Cloudformation termination protection manager**
- **Script**: `AWS_Cloudformation_termination_protection_manager.py`
- **Description**: Checks AWS Cloudformation for termination protection status and enables it
- **Location**: `AWS Cloudformation termination protection manager/`
- **Readme**: Details are provided in `AWS Cloudformation termination protection manager/readme.md`.


## Getting Started

### Prerequisites
- Python 3.6 or higher.
- AWS CLI configured with appropriate permissions.
- Required Python packages (install with `pip install -r requirements.txt` if specified).

### Running the Scripts
Each tool includes its own dedicated documentation in the respective `readme.md` file. Follow the instructions there for setup and execution.

### Example
For instance, to check security group exposure:

	cd "AWS Security Group Internet Exposure Checker"   
	python3 AWS_sg_internet_exposure_checker.py



## Contributing
Contributions are welcome! Feel free to submit issues or pull requests to improve these tools.


## Disclaimer
These scripts are provided as-is for educational purposes. Use them at your own risk. Ensure compliance with your organization's security and legal policies before running these tools in production environments.
