import os
from botocore.config import Config as BotoCoreConfig

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


class Settings:
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "test")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "test")
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    LOCALSTACK_ENDPOINT = os.getenv("LOCALSTACK_ENDPOINT", "http://localhost:4566")
    S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "mini-cloud-umkm-products")
    DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", "umkm_product_images")
    CONNECTION_TIMEOUT = int(os.getenv("CONNECTION_TIMEOUT", "3"))
    READ_TIMEOUT = int(os.getenv("READ_TIMEOUT", "5"))

    BOTO3_CONFIG = {
        "aws_access_key_id": AWS_ACCESS_KEY_ID,
        "aws_secret_access_key": AWS_SECRET_ACCESS_KEY,
        "region_name": AWS_REGION,
    }

    BOTOCORE_CLIENT_CONFIG = BotoCoreConfig(
        connect_timeout=CONNECTION_TIMEOUT,
        read_timeout=READ_TIMEOUT,
        retries={"max_attempts": 1, "mode": "standard"},
    )

    ALLOWED_IMAGE_FORMATS = ["JPG", "JPEG", "PNG", "WEBP"]
    DEFAULT_WATERMARK = "© UMKM Product"


settings = Settings()
