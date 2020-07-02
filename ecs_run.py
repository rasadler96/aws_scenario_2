import boto3
import yaml
import os
import botocore
import json

# Loading in Amazon credentials
amazon_config = yaml.safe_load(open("config.yml"))

amazon_details = amazon_config['amazon']
 
access_key = amazon_details['aws_access_key_id']
secret_key = amazon_details['aws_secret_access_key']
default_region = amazon_details['aws_default_region']

# Loading in ECS role ARNs, keypair name and security group id for those created in ecs_setup.py 
ecs_config = yaml.safe_load(open("ecs_config.yml"))

ecs_details = ecs_config['ecs_information']

ecsInstanceRole_arn = ecs_details['ecsInstanceRole_arn']
ecsS3InputBucketAccess_arn = ecs_details['ecsS3InputBucketAccess_arn']
ecsS3OutputBucketAccess_arn = ecs_details['ecsS3OutputBucketAccess_arn']
ecsTaskExecutionRole_arn = ecs_details['ecsTaskExecutionRole_arn']
keypair_name = ecs_details['keypair_name']
security_group_ID = ecs_details['security_group_ID']


# Creating session (configures credentials and default region)
session = boto3.Session(
	aws_access_key_id = access_key,
	aws_secret_access_key = secret_key,
	region_name = default_region
)

# Create cluster

def create_cluster(**kwargs):
    try:
        response = ecs_client.create_cluster(**kwargs)
    except botocore.exceptions.ClientError as e: 
        print(e)
    else: 
        cluster_name = response['cluster']['clusterName']
        print(response)
        return cluster_name

def run_task(**kwargs):
    try:
        response = ecs_client.run_task(**kwargs)
    except botocore.exceptions.ClientError as e:
        print(e)
    else:
        print(response)

# Setting up the required clients


ecs_client = boto3.client('ecs')

response = client.create_cluster(
    'clusterName'='t2-xlarge',
)


run_task = {
'cluster' : cluster_name,
'count' : 1,
'launchType' : 'EC2',
'placementStrategy' : [
    {
        'type': 'random',
    },
],
'referenceId' : 'task_id',
'taskDefinition' : taskARN
}


