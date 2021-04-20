# AWS Use Case 2 - ECS 

This code can be used to run ***one*** sample through a simple NGS pipeline created using publically available biocontainers, on AWS ECS. This code was created for the completion of an MSc project. 

## Prerequisites 

AWS programmatic access keys are required. These should be stored within a config file, in the format in the template config file. 

The sample to be run should be present in an input bucket within AWS S3. 


## Installation

1. Clone the repo
> git clone https://github.com/Becky-Sadler/DECIPHER_upload

2. Install requirements.txt in a virtualenv of your choice
> pip3 install -r requirements.txt

## Usage

## Future Work

### Changes to ecs_run.py 

1. Change instance and cluster provision from manual using Boto3 to IAC using CloudFront or Terraform. 
2. Allow multiple samples to be run by changing from sequential task running to a containerised pipeline using NextFlow or Cromwell. 