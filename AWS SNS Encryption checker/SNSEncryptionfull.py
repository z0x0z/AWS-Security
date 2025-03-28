import boto3
from rich.console import Console
from rich.table import Table
import time
from botocore.exceptions import ClientError

def validate_kms_key(kms_key_arn):
    try:
        # Extract region from the KMS key ARN
        region = kms_key_arn.split(':')[3]
        kms_client = boto3.client('kms', region_name=region)
        
        # Try to describe the key to verify it exists and is accessible
        response = kms_client.describe_key(KeyId=kms_key_arn)
        
        # Check if key is enabled
        if not response['KeyMetadata']['Enabled']:
            print(f'❌ KMS key {kms_key_arn} is disabled')
            return False
            
        # Check key state
        key_state = response['KeyMetadata']['KeyState']
        if key_state != 'Enabled':
            print(f'❌ KMS key {kms_key_arn} is in {key_state} state')
            return False
            
        print(f'✅ KMS key {kms_key_arn} is valid and enabled')
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NotFoundException':
            print(f'❌ KMS key {kms_key_arn} does not exist')
        elif error_code == 'InvalidArnException':
            print(f'❌ Invalid KMS key ARN format: {kms_key_arn}')
        else:
            print(f'❌ Error validating KMS key: {str(e)}')
        return False

def get_sns_topics(region):
    sns_client = boto3.client('sns', region_name=region)
    response = sns_client.list_topics()
    return response.get('Topics', [])

def check_topic_encryption(sns_client, topic_arn):
    attributes = sns_client.get_topic_attributes(TopicArn=topic_arn)['Attributes']
    return attributes.get('KmsMasterKeyId')

def verify_encryption(sns_client, topic_arn):
    time.sleep(2)
    encryption_status = check_topic_encryption(sns_client, topic_arn)
    if encryption_status:
        print(f'✅ Done')
        return True
    else:
        print(f'❌ Failed')
        return False

def encrypt_sns_topic(sns_client, topic_arn, kms_key_arn):
    try:
        sns_client.set_topic_attributes(
            TopicArn=topic_arn,
            AttributeName='KmsMasterKeyId',
            AttributeValue=kms_key_arn
        )
        print(f'Encrypting topic {topic_arn} with KMS key {kms_key_arn}')
        
        if verify_encryption(sns_client, topic_arn):
            print(f'Encryption successfully applied to topic {topic_arn}')
        else:
            print(f'Warning: Encryption may not have been properly applied to topic {topic_arn}')
            
    except Exception as e:
        print(f'Error encrypting topic {topic_arn}: {str(e)}')

def main():
    console = Console()
    table = Table(title="\nSNS Topics Encryption Status")
    table.add_column("Region", style="cyan", no_wrap=True)
    table.add_column("SNS Topic ARN", style="magenta", no_wrap=True, overflow="fold")
    table.add_column("Encryption Status", style="green")
    
    regions = [region['RegionName'] for region in boto3.client('ec2').describe_regions()['Regions']]
    
    region_topics = {}
    for region in regions:
        sns_client = boto3.client('sns', region_name=region)
        topics = get_sns_topics(region)
        region_topics[region] = topics
        
        for topic in topics:
            topic_arn = topic['TopicArn']
            encryption_status = check_topic_encryption(sns_client, topic_arn)
            encryption_status = encryption_status if encryption_status else "Not Encrypted"
            table.add_row(region, topic_arn, encryption_status)
    
    console.print(table)
    
    selected_regions = input("Enter the regions you want to process (comma-separated): ").split(',')
    
    # Get and validate KMS key ARN
    while True:
        kms_key_arn = input("Enter the KMS Key ARN to use for encryption: ").strip()
        if validate_kms_key(kms_key_arn):
            break
        retry = input("Would you like to enter a different KMS key ARN? (yes/no): ").strip().lower()
        if retry != 'yes':
            print("Exiting due to invalid KMS key.")
            return
    
    for region in selected_regions:
        region = region.strip()
        if region in region_topics:
            encrypt_all = input(f"\nDo you want to encrypt all SNS topics in {region}? (yes/no): ").strip().lower()
            sns_client = boto3.client('sns', region_name=region)
            
            if encrypt_all == 'yes':
                for topic in region_topics[region]:
                    encrypt_sns_topic(sns_client, topic['TopicArn'], kms_key_arn)
            else:
                topic_count = int(input(f"How many SNS topics in {region} do you want to encrypt? "))
                for _ in range(topic_count):
                    topic_name = input("Enter the SNS Topic ARN to encrypt: ")
                    encrypt_sns_topic(sns_client, topic_name, kms_key_arn)
    
    # Show final encryption status
    console.print("\n[bold cyan]Final encryption status for processed regions:[/bold cyan]")
    for region in selected_regions:
        region = region.strip()
        if region in region_topics:
            print(f"\nRegion: {region}")
            sns_client = boto3.client('sns', region_name=region)
            for topic in region_topics[region]:
                topic_arn = topic['TopicArn']
                encryption_status = check_topic_encryption(sns_client, topic_arn)
                status = "Encrypted" if encryption_status else "Not Encrypted"
                console.print(f"Topic: {topic_arn} - [bold cyan]{status}[/bold cyan]")
    
    more_regions = input("\nDo you want to process another region? (yes/no): ").strip().lower()
    if more_regions == 'yes':
        main()

if __name__ == "__main__":
    main()
