import boto3
from botocore.exceptions import ClientError
from os import path

EC2_RESOURCE = boto3.resource('ec2')
EC2_CLIENT = boto3.client('ec2')

def create_ec2(instance_type, sg_id, key_name, user_data, instance_name):
    """Creates an EC2 instance

    Args:
        instance_type (str): Instance type (m4.large, ...)
        sg_id (str): Security group ID
        key_name (str): SSH key name

    Returns:
        instance: The created instance object
    """
    instance = EC2_RESOURCE.create_instances(
        ImageId='ami-0149b2da6ceec4bb0',
        MinCount=1,
        MaxCount=1,
        UserData=user_data,
        InstanceType=instance_type,
        Monitoring={'Enabled': True},
        SecurityGroupIds=[sg_id],
        KeyName=key_name,
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': instance_name
                    },
                ]
            },
        ]
    )[0]
    print(f'{instance} is starting')
    return instance

def create_security_group(sg_name):
    """Creates a security group with the given name

    Args:
        sg_name (str): Security group name

    Returns:
        security_group_id: The created security group ID
    """
    security_group_id = None
    try:
        response = EC2_CLIENT.create_security_group(
            GroupName=sg_name,
            Description=f'Security group for {sg_name}'
        )
        security_group_id = response['GroupId']
        print(f'Successfully created security group {security_group_id}')

        # Define the security group rules here
        sec_group_rules = [
            {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
            {'IpProtocol': 'tcp', 'FromPort': 1186, 'ToPort': 1186, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
        ]

        data = EC2_CLIENT.authorize_security_group_ingress(GroupId=security_group_id, IpPermissions=sec_group_rules)
        print(f'Successfully updated security group rules with : {sec_group_rules}')
        return security_group_id
    except ClientError as e:
        try:  # if security group exists already, find the security group id
            response = EC2_CLIENT.describe_security_groups(
                Filters=[
                    dict(Name='group-name', Values=[sg_name])
                ])
            security_group_id = response['SecurityGroups'][0]['GroupId']
            print(f'Security group already exists with id {security_group_id}.')
            return security_group_id
        except ClientError as e:
            print(e)
            exit(1)