"""
config.py
Loads configuration from AWS Secrets Manager when running on Lambda,
or from .env when running locally.

Secret name in Secrets Manager: chitim-course-agent
Expected secret value (JSON):
{
    "IMAP_HOST": "imap.012.net.il",
    "IMAP_PORT": "143",
    "EMAIL_ADDRESS": "...",
    "EMAIL_PASSWORD": "...",
    "WP_ADMIN_URL": "https://meshek.chitim.co.il/wp-admin",
    "WP_ADMIN_USER": "...",
    "WP_ADMIN_PASSWORD": "...",
    "NEW_USER_PASSWORD": "1234",
    "CHECK_INTERVAL": "300"
}
"""

import json
import logging
import os

logger = logging.getLogger(__name__)

SECRET_NAME = "chitim-course"


def _load_from_secrets_manager() -> dict:
    import boto3
    from botocore.exceptions import ClientError

    client = boto3.client("secretsmanager")
    try:
        response = client.get_secret_value(SecretId=SECRET_NAME)
        return json.loads(response["SecretString"])
    except ClientError as e:
        logger.warning("Could not load from Secrets Manager: %s", e)
        return {}


def _load_from_env() -> dict:
    from dotenv import load_dotenv
    load_dotenv()
    return {
        "IMAP_HOST": os.getenv("IMAP_HOST", "mail.zahav.net.il"),
        "IMAP_PORT": os.getenv("IMAP_PORT", "993"),
        "EMAIL_ADDRESS": os.getenv("EMAIL_ADDRESS", ""),
        "EMAIL_PASSWORD": os.getenv("EMAIL_PASSWORD", ""),
        "WP_ADMIN_URL": os.getenv("WP_ADMIN_URL", "https://meshek.chitim.co.il/wp-admin"),
        "WP_ADMIN_USER": os.getenv("WP_ADMIN_USER", ""),
        "WP_ADMIN_PASSWORD": os.getenv("WP_ADMIN_PASSWORD", ""),
        "NEW_USER_PASSWORD": os.getenv("NEW_USER_PASSWORD", "1234"),
        "CHECK_INTERVAL": os.getenv("CHECK_INTERVAL", "300"),
    }


def load() -> dict:
    """
    Returns config dict. Uses Secrets Manager if running on Lambda
    (detected via AWS_LAMBDA_FUNCTION_NAME env var), otherwise uses .env.
    """
    if os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        logger.info("Running on Lambda — loading config from Secrets Manager.")
        cfg = _load_from_secrets_manager()
        if cfg:
            return cfg
        logger.warning("Secrets Manager returned empty — falling back to env vars.")

    return _load_from_env()
