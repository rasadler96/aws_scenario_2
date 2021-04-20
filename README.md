# AWS Use Case 2 - ECS 

This code can be used to run ***one*** sample through a simple NGS pipeline created using publically available biocontainers, on AWS ECS. Access to AWS resources is done through the software development kit, Boto3. This code was created for the completion of an MSc project. 

## Prerequisites 

AWS programmatic access keys are required. These should be stored within a config file, in the format in the template config file. 

The FASTQ files to be run should be present in an input bucket within AWS S3. 


## Installation

1. Clone the repo
> git clone https://github.com/Becky-Sadler/DECIPHER_upload

2. Install requirements.txt in a virtualenv of your choice
> pip3 install -r requirements.txt

## Usage

### ecs_setup.py

Input: 
- Config file for programmatic access to AWS. 

To run tasks on ECS, there are a number of different IAM roles that are required. The main purose of the ecs_setup.py is to set up the required roles for running the pipeline. In addition the script creates a key-pair to access instances within the ECS cluster and creates a security group to control traffic to and from instances in the cluster. 

The following roles are created within the AWS account being used: 

1. ecsInstanceRole : This role allows the container agent on each instance access to the ECS API to be able to communicate with ECS. 
2. ecsTaskExecutionRole : This role provides access to other AWS service resources that are required to run Amazon ECS tasks. 
3. ecsS3InputBucketAccess : This role provides access to the input bucket for ECS tasks. 
4. ecsS3OutputBucketAccess : This role provides access to the output bucket for ECS tasks.

Output: 
- The role ARNS, security group ID and keypair name are all then stored within a config file (ecs_config.yml)
- Keypair for EC2 instance access

### ecs_run.py 

## Future Work

### Changes to ecs_run.py 

1. Change instance and cluster provision from manual using Boto3 to IAC using CloudFront or Terraform. 
2. Allow multiple samples to be run by changing from sequential task running to a containerised pipeline using NextFlow or Cromwell. (Due to this change, the movement of the task registration is not being moved to ecs_setup) 