"""
AWS Lambda function for Songbird playlist synchronization
This function handles both scheduled and manual sync triggers
"""
import json
import os
import boto3
from datetime import datetime, timezone
from typing import Dict, Any

# Import Songbird modules
# Note: These would need to be packaged with the Lambda deployment
from songbird.sync.manager import SyncManager
from songbird.config.manager import ConfigManager


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    AWS Lambda handler for playlist synchronization

    Event sources:
    1. EventBridge (scheduled sync)
    2. API Gateway (manual sync)

    Args:
        event: Lambda event data
        context: Lambda context object

    Returns:
        Response with sync results
    """
    print(f"Lambda invoked with event: {json.dumps(event)}")

    try:
        # Determine trigger source
        trigger_source = _determine_trigger_source(event)
        print(f"Trigger source: {trigger_source}")

        # Initialize sync manager
        sync_manager = SyncManager()

        # Perform synchronization
        # verbose=True for CloudWatch logging, force=False to skip unchanged playlists
        sync_result = sync_manager.run_sync(verbose=True, force=False)

        # Prepare response
        response = {
            'success': sync_result,
            'trigger': trigger_source,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'message': 'Sync completed successfully' if sync_result else 'Sync failed'
        }

        # Log to CloudWatch
        print(f"Sync result: {response}")

        # For API Gateway, return HTTP response
        if trigger_source == 'api_gateway':
            return {
                'statusCode': 200 if sync_result else 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps(response)
            }

        # For EventBridge, return simple response
        return response

    except Exception as e:
        error_message = f"Lambda function error: {str(e)}"
        print(error_message)

        # Log error
        config_manager = ConfigManager()
        config_manager.log_error('lambda_error', error_message, {'event': event})

        # Return error response
        error_response = {
            'success': False,
            'error': error_message,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        if _determine_trigger_source(event) == 'api_gateway':
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps(error_response)
            }

        return error_response


def _determine_trigger_source(event: Dict[str, Any]) -> str:
    """Determine the source of the Lambda trigger"""

    # API Gateway trigger
    if 'httpMethod' in event or 'requestContext' in event:
        return 'api_gateway'

    # EventBridge trigger
    if 'source' in event and event['source'] == 'aws.events':
        return 'eventbridge'

    # Direct Lambda invocation
    if 'trigger' in event:
        return event['trigger']

    # Default
    return 'unknown'


def _load_config_from_s3() -> Dict:
    """
    Load configuration from S3
    This would replace local file-based config in production
    """
    try:
        s3_client = boto3.client('s3')
        bucket_name = os.environ.get('SONGBIRD_CONFIG_BUCKET')
        config_key = 'config/songbird_config.json'

        response = s3_client.get_object(Bucket=bucket_name, Key=config_key)
        config_data = json.loads(response['Body'].read())

        return config_data

    except Exception as e:
        print(f"Failed to load config from S3: {e}")
        return {}


def _save_config_to_s3(config: Dict) -> bool:
    """
    Save configuration to S3
    This would replace local file-based config in production
    """
    try:
        s3_client = boto3.client('s3')
        bucket_name = os.environ.get('SONGBIRD_CONFIG_BUCKET')
        config_key = 'config/songbird_config.json'

        s3_client.put_object(
            Bucket=bucket_name,
            Key=config_key,
            Body=json.dumps(config, indent=2),
            ContentType='application/json'
        )

        return True

    except Exception as e:
        print(f"Failed to save config to S3: {e}")
        return False


def _get_secrets_from_parameter_store() -> Dict[str, str]:
    """
    Get API secrets from AWS Systems Manager Parameter Store
    This is more secure than environment variables
    """
    try:
        ssm_client = boto3.client('ssm')

        # Get Spotify credentials
        spotify_client_id = ssm_client.get_parameter(
            Name='/songbird/spotify/client_id',
            WithDecryption=True
        )['Parameter']['Value']

        spotify_client_secret = ssm_client.get_parameter(
            Name='/songbird/spotify/client_secret',
            WithDecryption=True
        )['Parameter']['Value']

        # Get Apple Music credentials
        apple_team_id = ssm_client.get_parameter(
            Name='/songbird/apple/team_id',
            WithDecryption=True
        )['Parameter']['Value']

        apple_key_id = ssm_client.get_parameter(
            Name='/songbird/apple/key_id',
            WithDecryption=True
        )['Parameter']['Value']

        return {
            'SPOTIFY_CLIENT_ID': spotify_client_id,
            'SPOTIFY_CLIENT_SECRET': spotify_client_secret,
            'APPLE_TEAM_ID': apple_team_id,
            'APPLE_KEY_ID': apple_key_id
        }

    except Exception as e:
        print(f"Failed to get secrets from Parameter Store: {e}")
        return {}


# For local testing
if __name__ == '__main__':
    # Test event for manual trigger
    test_event = {
        'trigger': 'manual',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }

    result = lambda_handler(test_event, None)
    print(f"Test result: {json.dumps(result, indent=2)}")