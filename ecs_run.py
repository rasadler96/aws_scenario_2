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
        task_def_arn = response["taskDefinition"]["taskDefinitionArn"]
        log_group = response["taskDefinition"]["containerDefinitions"][0]["logConfiguration"]["options"]["awslogs-group"]
        print('Task %s registered'%task_def_arn)
        return task_def_arn, log_group

def create_log_group(log_group):
    try:
        response = log_client.create_log_group(logGroupName=log_group)
    except botocore.exceptions.ClientError as e:
        print(e)
    else:
        print('Log group created: %s'%log_group)

def create_cluster(**kwargs):
    try:
        response = ecs_client.create_cluster(**kwargs)
    except botocore.exceptions.ClientError as e: 
        print(e)
    else: 
        cluster_name = response['cluster']['clusterName']
        print('Cluster (%s) created'%cluster_name)
        return cluster_name

def create_instances(**kwargs):
    try:
        response = ec2_client.run_instances(**kwargs)
    except botocore.exceptions.ClientError as e: 
        print(e)
    else:
        instance_ID = response['Instances'][0]['InstanceId']
        print('Instance created (%s)'%instance_ID)
        return instance_ID  

def add_waiter(waiter_type, **kwargs):
    try:
        waiter = ec2_client.get_waiter(waiter_type)
        waiter.wait(**kwargs)
    except botocore.exceptions.ClientError as e: 
        print(e)
    else:
        print(waiter_type)

def run_task(cluster_name, task_definition_arn):
    try:
        response = ecs_client.run_task(
            cluster = cluster_name,
            count = 1,
            launchType = 'EC2',
            placementStrategy = [
                {
                    'type': 'random',
                },
            ],
            referenceId= 'task_id',
            taskDefinition= task_definition_arn)
    except botocore.exceptions.ClientError as e:
        print(e)
    else:
        # If task runs without error, pull the task_arn from the response
        task_arn = response['tasks'][0]['containers'][0]['taskArn']
        
        # Wait for task to stop
        waiter = ecs_client.get_waiter('tasks_stopped')
        waiter.wait(
            cluster=cluster_name,
            tasks=[
                task_arn,
            ],
            WaiterConfig={
                'Delay': 60,
                'MaxAttempts': 1000
            }
        )

        # Describe the task to get the exit code - should be 0. 
        describe_tasks = ecs_client.describe_tasks(
            cluster=cluster_name,
            tasks=[
                task_arn,
            ]
        )
        exit_code = describe_tasks['tasks'][0]['containers'][0]['exitCode']
        print('%s complete with exit code %s'%(task_arn, exit_code))

def terminate_instance_cluster(instanceID, cluster_name):
    try:
        ec2_resource.instances.filter(InstanceIds=[instanceID]).terminate()
        
        # Wait for instance to be terminated 
        waiter = ec2_client.get_waiter('instance_terminated')
        waiter.wait(
            InstanceIds=[
                instanceID,
            ],
            WaiterConfig={
                'Delay': 20,
                'MaxAttempts': 100
            }
        )

        # Delete cluster
        ecs_client.delete_cluster(cluster=cluster_name)
    except botocore.exceptions.ClientError as e:
        print(e)
    else:
        print('Instance terminated and cluster deleted')

# Loading in Amazon credentials
amazon_config = yaml.safe_load(open("config.yml"))

amazon_details = amazon_config['amazon']
 
access_key = amazon_details['aws_access_key_id']
secret_key = amazon_details['aws_secret_access_key']
default_region = amazon_details['aws_default_region']

# Loading in ECS role ARNs, keypair name and security group id for those created in ecs_setup.py 
ecs_config = yaml.safe_load(open("ecs_config.yml"))

ecs_details = ecs_config['ecs_information']

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
ec2_resource = session.resource('ec2')
log_client = session.client('logs')

# Creating list of the JSON files needed to create a task for each pipeline step
json_files = []
json_files.extend(glob.glob('./JSON/*.json'))

task_def_arn_dict = {}

for file in json_files:
    user_data = get_task_JSON(file)
    base=os.path.basename(file)
    process = os.path.splitext(base)[0]
    # Register task
    task_def_arn, log_group = register_task(**user_data)
    # Add name of task and the ARN to a dictionary
    task_def_arn_dict.update( {process : task_def_arn} ) 
    # Create cloudwatch log group for task
    create_log_group(log_group)

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

# Waiter for initilisation of the instance - to give time for the instance to register with the cluster. 
waiter_initilised = {
    'InstanceIds' : [instance_id],
    'WaiterConfig' : {
        'Delay': 30,
        'MaxAttempts': 100
    }
}

add_waiter('instance_status_ok', **waiter_initilised)

# Creating a list of the task arns in pipeline order
pipeline_steps = [task_def_arn_dict['s3_pull'], task_def_arn_dict['align_bwa_mem'], task_def_arn_dict['sam_to_bam'], task_def_arn_dict['sort_sam'], task_def_arn_dict['index_bam'], task_def_arn_dict['mark_duplicates'], task_def_arn_dict['index_dedup'], task_def_arn_dict['variant_caller'], task_def_arn_dict['push_to_s3']]

# Running each pipeline task
for step in pipeline_steps:
    run_task(cluster_name, step)


# Terminate the instance and delete cluster as no longer required. 
terminate_instance_cluster(instance_id, cluster_name)


