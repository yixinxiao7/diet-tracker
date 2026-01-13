import json
import os
import psycopg2
import boto3

# Cached across Lambda invocations (warm starts)
_connection = None
_secret_cache = None


def _get_db_secret():
    global _secret_cache

    if _secret_cache:
        return _secret_cache

    secret_arn = os.environ["DB_SECRET_ARN"]

    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=secret_arn)

    _secret_cache = json.loads(response["SecretString"])
    return _secret_cache


def get_connection():
    global _connection

    if _connection and _connection.closed == 0:
        return _connection

    secret = _get_db_secret()

    _connection = psycopg2.connect(
        host=secret["host"],
        user=secret["username"],
        password=secret["password"],
        port=secret.get("port", 5432),
        dbname=os.environ["DB_NAME"],
        connect_timeout=5
    )

    return _connection
