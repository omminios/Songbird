"""
S3 utility functions for Songbird
Shared functionality for S3 operations across the application
"""
import os
import json
from typing import Dict, Any


def validate_s3_bucket() -> str:
    """
    Validate that SONGBIRD_CONFIG_BUCKET environment variable is set

    Returns:
        str: The S3 bucket name

    Raises:
        ValueError: If SONGBIRD_CONFIG_BUCKET is not set
    """
    bucket = os.getenv('SONGBIRD_CONFIG_BUCKET')
    if not bucket:
        raise ValueError(
            "Missing SONGBIRD_CONFIG_BUCKET environment variable.\n"
            "Please set it to your S3 bucket name:\n"
            "  export SONGBIRD_CONFIG_BUCKET=your-bucket-name"
        )
    return bucket


def save_json_to_s3(s3_client, bucket: str, key: str, data: Dict[str, Any]) -> None:
    """
    Save JSON data to S3 with standard encryption and formatting

    Args:
        s3_client: boto3 S3 client instance
        bucket: S3 bucket name
        key: S3 object key (path within bucket)
        data: Dictionary to save as JSON

    Raises:
        Exception: If S3 write operation fails
    """
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(data, indent=2),
        ServerSideEncryption='AES256',
        ContentType='application/json'
    )


def load_json_from_s3(s3_client, bucket: str, key: str) -> Dict[str, Any]:
    """
    Load JSON data from S3

    Args:
        s3_client: boto3 S3 client instance
        bucket: S3 bucket name
        key: S3 object key (path within bucket)

    Returns:
        Dictionary loaded from S3 JSON file

    Raises:
        s3_client.exceptions.NoSuchKey: If the specified key doesn't exist
        Exception: If S3 read or JSON parsing fails
    """
    response = s3_client.get_object(Bucket=bucket, Key=key)
    return json.loads(response['Body'].read())
