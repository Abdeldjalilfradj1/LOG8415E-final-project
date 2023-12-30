import boto3
from botocore.exceptions import ClientError
from os import path

EC2_RESOURCE = boto3.resource('ec2')
EC2_CLIENT = boto3.client('ec2')