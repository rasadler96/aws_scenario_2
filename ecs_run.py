import boto3
import yaml
import os
import botocore

amazon_config = yaml.safe_load(open("config.yml"))

amazon_details = amazon_config['amazon']
 
access_key = amazon_details['aws_access_key_id']
secret_key = amazon_details['aws_secret_access_key']
default_region = amazon_details['aws_default_region']

# Creating session (configures credentials and default region)
session = boto3.Session(
	aws_access_key_id = access_key,
	aws_secret_access_key = secret_key,
	region_name = default_region
)

ecs_client = boto3.client('ecs')

# Create cluster

def create_cluster(**kwargs):
    try:
        response = ecs_client.create_cluster(**kwargs)
    except botocore.exceptions.ClientError as e: 
        print(e)
    else: 
        print(response)

cluster_details = {
'clusterName': 'test_cluster',
'settings' : [
    {
        'name': 'containerInsights',
        'value': 'string'
    },
],
'capacityProviders' : [
    'string',
],
'defaultCapacityProviderStrategy' : [
    {
        'capacityProvider': 'string',
        'weight': 123,
        'base': 123
    },
]}
