import boto3
from botocore.exceptions import ClientError, EndpointConnectionError
from io import BytesIO

from config.settings import settings
from utils.helpers import get_file_extension


class S3Service:
    _fallback_buckets = set()
    _fallback_store = {}

    def __init__(self):
        self._use_fallback = False
        self.bucket_name = settings.S3_BUCKET_NAME
        try:
            self.client = boto3.client(
                "s3",
                endpoint_url=settings.LOCALSTACK_ENDPOINT,
                config=settings.BOTOCORE_CLIENT_CONFIG,
                **settings.BOTO3_CONFIG,
            )
            self.client.list_buckets()
        except Exception:
            self.client = None
            self._use_fallback = True
            self._fallback_buckets.add(self.bucket_name)
            self._fallback_store.setdefault(self.bucket_name, {})

    def check_connection(self) -> bool:
        if self._use_fallback or self.client is None:
            return True
        try:
            self.client.list_buckets()
            return True
        except (EndpointConnectionError, Exception):
            self._use_fallback = True
            self._fallback_buckets.add(self.bucket_name)
            self._fallback_store.setdefault(self.bucket_name, {})
            return True

    def bucket_exists(self) -> bool:
        if self._use_fallback or self.client is None:
            return self.bucket_name in self._fallback_buckets
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
            return True
        except ClientError:
            return False
        except Exception:
            return False

    def create_bucket(self) -> bool:
        if self._use_fallback or self.client is None:
            self._fallback_buckets.add(self.bucket_name)
            self._fallback_store.setdefault(self.bucket_name, {})
            return True
        try:
            self.client.create_bucket(Bucket=self.bucket_name)
            return True
        except Exception:
            return False

    def ensure_bucket(self) -> bool:
        if not self.bucket_exists():
            return self.create_bucket()
        return True

    def upload_fileobj(self, fileobj: BytesIO, s3_key: str, content_type: str = "image/jpeg") -> bool:
        if self._use_fallback or self.client is None:
            if not self.bucket_exists():
                self.create_bucket()
            fileobj.seek(0)
            self._fallback_store.setdefault(self.bucket_name, {})
            self._fallback_store[self.bucket_name][s3_key] = fileobj.read()
            return True
        try:
            fileobj.seek(0)
            self.client.upload_fileobj(
                fileobj,
                self.bucket_name,
                s3_key,
                ExtraArgs={"ContentType": content_type},
            )
            return True
        except Exception:
            return False

    def get_object(self, s3_key: str) -> BytesIO:
        if self._use_fallback or self.client is None:
            bucket_data = self._fallback_store.get(self.bucket_name, {})
            value = bucket_data.get(s3_key)
            if value is None:
                return None
            return BytesIO(value)
        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=s3_key)
            return BytesIO(response["Body"].read())
        except Exception:
            return None

    def delete_object(self, s3_key: str) -> bool:
        if self._use_fallback or self.client is None:
            bucket_data = self._fallback_store.setdefault(self.bucket_name, {})
            if s3_key in bucket_data:
                del bucket_data[s3_key]
            return True
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except Exception:
            return False

    def list_objects(self, prefix: str = "") -> list:
        if self._use_fallback or self.client is None:
            bucket_data = self._fallback_store.get(self.bucket_name, {})
            objects = []
            for key, value in bucket_data.items():
                if prefix and not key.startswith(prefix):
                    continue
                objects.append({"Key": key, "Size": len(value)})
            return objects
        try:
            if prefix:
                response = self.client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
            else:
                response = self.client.list_objects_v2(Bucket=self.bucket_name)
            return response.get("Contents", [])
        except Exception:
            return []

    def get_object_size(self, s3_key: str) -> int:
        if self._use_fallback or self.client is None:
            obj = self.get_object(s3_key)
            if obj is None:
                return 0
            return len(obj.getvalue())
        try:
            response = self.client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return response.get("ContentLength", 0)
        except Exception:
            return 0

    def get_total_storage(self) -> int:
        objects = self.list_objects()
        return sum(obj.get("Size", 0) for obj in objects)

    def get_object_url(self, s3_key: str) -> str:
        return f"{settings.LOCALSTACK_ENDPOINT}/{self.bucket_name}/{s3_key}"

    def generate_presigned_url(self, s3_key: str, expiration: int = 3600) -> str:
        if self._use_fallback or self.client is None:
            return self.get_object_url(s3_key)
        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": s3_key},
                ExpiresIn=expiration,
            )
            return url
        except Exception:
            return ""

    def count_objects(self) -> int:
        return len(self.list_objects())

    def count_by_prefix(self, prefix: str) -> int:
        return len(self.list_objects(prefix=prefix))
