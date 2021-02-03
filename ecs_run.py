import boto3
import yaml
import os
import botocore
import json
import glob

def get_task_JSON(file_name):
    with open(file_name) as f:
        user_data = json.load(f)
    return user_data

def register_task(**kwargs):
    try:
        response = ecs_client.register_task_definition(**kwargs)
    except botocore.exceptions.ClientError as e:
        print(e)
    else: 
        task_arn = response["taskDefinition"]["taskDefinitionArn"]
        print('Task %s registered'%task_arn)
        return task_arn

def create_cluster(**kwargs):
    try:
        response = ecs_client.create_cluster(**kwargs)
    except botocore.exceptions.ClientError as e: 
        print(e)
    else: 
        cluster_name = response['cluster']['clusterName']
        return cluster_name

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

# Setting up the required clients

ecs_client = session.client('ecs')
ec2_client = session.client('ec2')

# Creating list of the JSON files needed to create a task for each pipeline step
json_files = []
json_files.extend(glob.glob('./JSON/*.json'))

task_arn_dict = {}

for file in json_files:
    user_data = get_task_JSON(file)
    base=os.path.basename(file)
    process = os.path.splitext(base)[0]
    # Register task
    task_arn = register_task(**user_data)
    # Add name of task and the ARN to a dictionary
    task_arn_dict.update( {process : task_arn} ) 

# Defining cluster details then creating cluster
cluster_details = {
    'clusterName' : 'pipeline_cluster'
}

cluster_name = create_cluster(**cluster_details)


# User data required to point the EC2 instance to the cluster created.

user_data = '#!/bin/bash \necho ECS_CLUSTER=' + cluster_name + ' >> /etc/ecs/ecs.config'

# Defining the EC2 instance details : Use the ECS Amazon Linux 2 AMI - minimum volume of 30 for the snapshot. 
instance_details = {'BlockDeviceMappings' : [
    {
        'DeviceName' : '/dev/xvda',
        'Ebs': {
            'DeleteOnTermination': True,
            'VolumeSize': 30,
            'VolumeType': 'gp2',
            'Encrypted': False
        },
    },
],
'ImageId' : 'ami-0cd4858f2b923aa6b',
'InstanceType' : 't2.xlarge',
'KeyName' : keypair_name,
'MinCount' : 1,
'MaxCount' : 1,
'SecurityGroupIds' : [
    security_group_ID,
],
'UserData' : user_data,
'IamInstanceProfile' : {
    'Name': 'ecsInstanceRole',
    }}

instance_id = create_instances(**instance_details)










