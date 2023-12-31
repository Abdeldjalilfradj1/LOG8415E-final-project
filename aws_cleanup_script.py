import boto3
from botocore.exceptions import ClientError


def terminate_instances(ec2_client):
    # Describe all instances
    response = ec2_client.describe_instances()
    instances_to_terminate = []

    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            # Check if the instance is running
            if instance['State']['Name'] == 'running':
                instances_to_terminate.append(instance['InstanceId'])

    # Terminate instances
    if instances_to_terminate:
        print(f"Terminating instances: {instances_to_terminate}")
        ec2_client.terminate_instances(InstanceIds=instances_to_terminate)
    else:
        print("No running instances found.")


def delete_security_groups(ec2_client):
    # Describe all security groups
    response = ec2_client.describe_security_groups()

    for security_group in response['SecurityGroups']:
        try:
            # Default security group cannot be deleted
            if security_group['GroupName'] != 'default':
                print(f"Deleting security group: {security_group['GroupId']}")
                ec2_client.delete_security_group(GroupId=security_group['GroupId'])
        except ClientError as e:
            print(f"Error deleting security group {security_group['GroupId']}: {e}")


def main():
    ec2_client = boto3.client('ec2')

    terminate_instances(ec2_client)
    delete_security_groups(ec2_client)


if __name__ == "__main__":
    main()
