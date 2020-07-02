import boto3
import yaml
import os
import botocore
import json

# To debug 
#boto3.set_stream_logger('botocore', level='DEBUG')

amazon_config = yaml.safe_load(open("config.yml"))

amazon_details = amazon_config['amazon']
 
access_key = amazon_details['aws_access_key_id']
secret_key = amazon_details['aws_secret_access_key']
default_region = amazon_details['aws_default_region']

# Bucket details 

bucket_details = amazon_config['buckets']
input_bucket = bucket_details['input_bucket_arn']
output_bucket = bucket_details['output_bucket_arn']
input_bucket_files = input_bucket + '/*'
output_bucket_files = output_bucket + '/*'

# Creating session (configures credentials and default region)
session = boto3.Session(
	aws_access_key_id = access_key,
	aws_secret_access_key = secret_key,
	region_name = default_region
)

# Setting up the required clients

ecs_client = session.client('ecs', region_name=default_region)
iam_client = session.client('iam')
ec2_resource = session.resource('ec2', region_name=default_region)
ec2_client = session.client('ec2', region_name=default_region)

# List of required functions

# Function to create a key-pair for the instances in the cluster
def create_keypair(name_of_keypair):
	key_file = open('%s.pem'%name_of_keypair,'w')
	try:
		key = ec2_resource.create_key_pair(KeyName=name_of_keypair)
		key_pair_contents = str(key.key_material)
		key_file.write(key_pair_contents)
		os.system('chmod 400 %s.pem'%name_of_keypair)
	except botocore.exceptions.ClientError as e: 
		print(e)
	else:
		print('Key pair %s.pem sucessfully created'%name_of_keypair)
		return(name_of_keypair)

# Function to create security group to be used for cluster
def create_security_group(description, name):
	try:
		response = ec2_client.create_security_group(
			Description = description,
			GroupName = name
		)
	except botocore.exceptions.ClientError as e: 
		print(e)
	else:
		print('Security group sucessfully created')	
		sg_id = response['GroupId']
		return(sg_id)

# Function to create security group that give SSH access to instances in the cluster.
def create_sg_rule(groupid, ipPermissions):
	try:	
		response = ec2_client.authorize_security_group_ingress(
		GroupId= groupid,
		#GroupName='string',
		IpPermissions= ipPermissions
	)
	except botocore.exceptions.ClientError as e: 
		print(e)
	else:
		print('Security group rule added: %s'%ipPermissions)	

# Create IAM role
def create_iam_role(**kwargs):
	try:
		response = iam_client.create_role(**kwargs)
	except botocore.exceptions.ClientError as e:
		print(e)
	else:
		role_arn = response['Role']['Arn']
		role_name = response['Role']['RoleName']
		print('IAM role %s created'%role_name)
		return role_arn, role_name 

def create_policy(PolicyName, policy_json):
	try:
		response = iam_client.create_policy(
			PolicyName = PolicyName,
			PolicyDocument = json.dumps(policy_json),
			)
	except botocore.exceptions.ClientError as e:
		print(e)
	else:
		policy_arn = response['Policy']['Arn']
		print('%s added' %policy_arn)
		return policy_arn

# Add policy to IAM rule
def add_policy(policy_arn, role_name):
	try:
		iam_client.attach_role_policy(
		PolicyArn=policy_arn,
		RoleName=role_name
		)
	except botocore.exceptions.ClientError as e:
		print(e)
	else:
		print('%s policy added to %s' %(policy_arn, role_name))

# Create instance profile (Needed to attach role to an instance)
def create_instance_profile(instance_profile_name):
	try:
		iam_client.create_instance_profile(
			InstanceProfileName = instance_profile_name
		)
	except botocore.exceptions.ClientError as e:
		print(e)
	else:
		print('Instance profile %s created'%instance_profile_name)

# Add role to instance profile
def add_role_to_instance_profile(instance_profile_name, role_name):
	try:
		iam_client.add_role_to_instance_profile(
			InstanceProfileName= instance_profile_name,
			RoleName= role_name
		)
	except botocore.exceptions.ClientError as e:
		print(e)
	else:
		print('Role added to instance profile')

# Registering the task definitions for each step in the pipeline. 
def register_task_definition(**kwargs):
	try:
		response = ecs_client.register_task_definition(**kwargs)
	except botocore.exceptions.ClientError as e:
		print(e)
	else:
		print(response)

def add_to_config(keypairName, sgID, role1ARN, role2ARN, role3ARN, role4ARN):
	data = {'ecs_information': {'keypair_name': str(keypairName), 'security_group_ID': str(sgID), 'ecsInstanceRole_arn' : str(role1ARN), 'ecsTaskExecutionRole_arn' : str(role2ARN), 'ecsS3InputBucketAccess_arn' : str(role3ARN), 'ecsS3OutputBucketAccess_arn' : str(role4ARN)}}
	config_file = open('ecs_config.yml', 'w')
	yaml.dump(data, config_file)
	print('ecs_config file created')

# Create key pair 


key_name = create_keypair('ecs_key')

# Create ECS security group
security_group_id = create_security_group('Security group for ECS Scenario 2', 'ECS group')

# Defining a security group rule - this allows SSH access to the instance 
ipPermissions =[
		{
			'FromPort': 22,
			'IpProtocol': 'tcp',
			'IpRanges': [
				{
					'CidrIp': '0.0.0.0/0',
					'Description': 'SSH access',
				},
			],
			'ToPort': 22,
		}
	]

# Adding rule to the security group 
create_sg_rule(security_group_id, ipPermissions)

# Creating an IAM role for EC2 to access S3 

# Create a trust permission for both EC2 and ECS-Tasks (giving EC2 and ecs-tasks ability to take on the role created)

ecs_task_role_access = {
  "Version": "2012-10-17",
  "Statement": [
	{
	  "Sid": "",
	  "Effect": "Allow",
	  "Principal": {
		"Service": "ecs-tasks.amazonaws.com"
	  },
	  "Action": "sts:AssumeRole"
	}
  ]
}

ec2_role_access = {
  "Version": "2012-10-17",
  "Statement": [
	{
	  "Sid": "",
	  "Effect": "Allow",
	  "Principal": {
		"Service": "ec2.amazonaws.com"
	  },
	  "Action": "sts:AssumeRole"
	}
  ]
}

# Creating the four required roles:
ecsInstanceRole = {
'RoleName':'ecsInstanceRole',
'AssumeRolePolicyDocument' : json.dumps(ec2_role_access),
'Description':'Role to give EC2 access to Amazon EC2 Container Service.',
'MaxSessionDuration' : 43200}

ecsTaskExecutionRole = {
'RoleName':'ecsTaskExecutionRole',
'AssumeRolePolicyDocument' : json.dumps(ecs_task_role_access),
'Description':'Role to provide access to other AWS service resources that are required to run Amazon ECS tasks',
'MaxSessionDuration' : 43200}

ecsS3InputBucketAccess = {
'RoleName':'ecsS3InputBucketAccess',
'AssumeRolePolicyDocument' : json.dumps(ecs_task_role_access),
'Description':'Role to provide access to input bucket to ecs tasks',
'MaxSessionDuration' : 43200}

ecsS3OutputBucketAccess = {
'RoleName':'ecsS3OutputBucketAccess',
'AssumeRolePolicyDocument' : json.dumps(ecs_task_role_access),
'Description':'Role to provide access to output bucket to ecs tasks',
'MaxSessionDuration' : 43200}

# Creating the roles
ecsInstanceRole_arn, ecsInstanceRole_name = create_iam_role(**ecsInstanceRole)
ecsTaskExecutionRole_arn, ecsTaskExecutionRole_name = create_iam_role(**ecsTaskExecutionRole)
ecsS3InputBucketAccess_arn, ecsS3InputBucketAccess_name = create_iam_role(**ecsS3InputBucketAccess)
ecsS3OutputBucketAccess_arn, ecsS3OutputBucketAccess_name = create_iam_role(**ecsS3OutputBucketAccess)

# Adding the aws managed policies to ecsInstanceRole and ecsTaskExecutionRole
add_policy('arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role', ecsInstanceRole_name)
add_policy('arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy', ecsTaskExecutionRole_name)

# Create policies for ecsS3InputBucketAccess and ecsS3OutputBucketAccess roles

input_bucket_access = {
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": [input_bucket]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject"
      ],
      "Resource": [input_bucket_files]
    }
  ]
}

output_bucket_access = {
   "Version":"2012-10-17",
   "Statement":[
	  {
		 "Effect":"Allow",
		 "Action":[
			"s3:ListBucket"
		 ],
		 "Resource": [output_bucket]
	  },
	  {
		 "Effect":"Allow",
		 "Action":[
			"s3:PutObject"
		 ],
		 "Resource": [output_bucket_files]
	  }
   ]
}

input_policy = create_policy('ecsS3InputBucketAccess_policy', input_bucket_access)
output_policy = create_policy('ecsS3OutputBucketAccess_policy', output_bucket_access)

# Adding the created policies to ecsS3InputBucketAccess and ecsS3OutputBucketAccess roles

add_policy(input_policy, ecsS3InputBucketAccess_name)
add_policy(output_policy , ecsS3OutputBucketAccess_name)

# Create instance profiles and add roles -> Name of instance profile == same as role name (makes it easier and is how this occurs if done through the console)

# ecsInstanceRole 
create_instance_profile(ecsInstanceRole_name)
add_role_to_instance_profile(ecsInstanceRole_name, ecsInstanceRole_name)

# ecsTaskExecutionRole
create_instance_profile(ecsTaskExecutionRole_name)
add_role_to_instance_profile(ecsTaskExecutionRole_name, ecsTaskExecutionRole_name)

# ecsS3InputBucketAccess
create_instance_profile(ecsS3InputBucketAccess_name)
add_role_to_instance_profile(ecsS3InputBucketAccess_name, ecsS3InputBucketAccess_name)

# ecsS3OutputBucketAccess
create_instance_profile(ecsS3OutputBucketAccess_name)
add_role_to_instance_profile(ecsS3OutputBucketAccess_name, ecsS3OutputBucketAccess_name)

# Load information into config file: 

add_to_config(key_name, security_group_id, ecsInstanceRole_arn, ecsTaskExecutionRole_arn, ecsS3InputBucketAccess_arn, ecsS3OutputBucketAccess_arn)

