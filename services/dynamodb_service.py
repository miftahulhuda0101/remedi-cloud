import boto3
from botocore.exceptions import ClientError, EndpointConnectionError
import time

from config.settings import settings


class DynamoDBService:
    _fallback_tables = set()
    _fallback_store = {}

    def __init__(self):
        self._use_fallback = False
        self.table_name = settings.DYNAMODB_TABLE_NAME
        try:
            self.resource = boto3.resource(
                "dynamodb",
                endpoint_url=settings.LOCALSTACK_ENDPOINT,
                config=settings.BOTOCORE_CLIENT_CONFIG,
                **settings.BOTO3_CONFIG,
            )
            self.client = boto3.client(
                "dynamodb",
                endpoint_url=settings.LOCALSTACK_ENDPOINT,
                config=settings.BOTOCORE_CLIENT_CONFIG,
                **settings.BOTO3_CONFIG,
            )
            self.client.list_tables()
        except Exception:
            self.resource = None
            self.client = None
            self._use_fallback = True
            self._fallback_tables.add(self.table_name)
            self._fallback_store.setdefault(self.table_name, {})

    def check_connection(self) -> bool:
        if self._use_fallback or self.client is None:
            return True
        try:
            self.client.list_tables()
            return True
        except (EndpointConnectionError, Exception):
            self._use_fallback = True
            self._fallback_tables.add(self.table_name)
            self._fallback_store.setdefault(self.table_name, {})
            return True

    def table_exists(self) -> bool:
        if self._use_fallback or self.client is None:
            return self.table_name in self._fallback_tables
        try:
            self.client.describe_table(TableName=self.table_name)
            return True
        except ClientError:
            return False
        except Exception:
            return False

    def create_table(self) -> bool:
        if self._use_fallback or self.client is None:
            self._fallback_tables.add(self.table_name)
            self._fallback_store.setdefault(self.table_name, {})
            return True
        try:
            self.resource.create_table(
                TableName=self.table_name,
                KeySchema=[
                    {"AttributeName": "image_id", "KeyType": "HASH"},
                ],
                AttributeDefinitions=[
                    {"AttributeName": "image_id", "AttributeType": "S"},
                ],
                ProvisionedThroughput={
                    "ReadCapacityUnits": 5,
                    "WriteCapacityUnits": 5,
                },
            )
            self.wait_for_table_active()
            return True
        except Exception:
            return False

    def wait_for_table_active(self, timeout: int = 60) -> bool:
        if self._use_fallback or self.client is None:
            return True
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = self.client.describe_table(TableName=self.table_name)
                if response["Table"]["TableStatus"] == "ACTIVE":
                    return True
            except Exception:
                pass
            time.sleep(1)
        return False

    def ensure_table(self) -> bool:
        if not self.table_exists():
            return self.create_table()
        return True

    def put_item(self, item: dict) -> bool:
        if self._use_fallback or self.resource is None or self.client is None:
            self._fallback_store.setdefault(self.table_name, {})
            image_id = item.get("image_id")
            if image_id is None:
                return False
            self._fallback_store[self.table_name][image_id] = item
            return True
        try:
            table = self.resource.Table(self.table_name)
            table.put_item(Item=item)
            return True
        except Exception:
            return False

    def get_item(self, image_id: str) -> dict:
        if self._use_fallback or self.resource is None or self.client is None:
            return self._fallback_store.get(self.table_name, {}).get(image_id)
        try:
            table = self.resource.Table(self.table_name)
            response = table.get_item(Key={"image_id": image_id})
            return response.get("Item", None)
        except Exception:
            return None

    def delete_item(self, image_id: str) -> bool:
        if self._use_fallback or self.resource is None or self.client is None:
            self._fallback_store.setdefault(self.table_name, {})
            self._fallback_store[self.table_name].pop(image_id, None)
            return True
        try:
            table = self.resource.Table(self.table_name)
            table.delete_item(Key={"image_id": image_id})
            return True
        except Exception:
            return False

    def scan_all(self) -> list:
        if self._use_fallback or self.resource is None or self.client is None:
            return list(self._fallback_store.get(self.table_name, {}).values())
        try:
            table = self.resource.Table(self.table_name)
            response = table.scan()
            items = response.get("Items", [])
            while "LastEvaluatedKey" in response:
                response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
                items.extend(response.get("Items", []))
            return items
        except Exception:
            return []

    def count_items(self) -> int:
        if self._use_fallback or self.resource is None or self.client is None:
            return len(self._fallback_store.get(self.table_name, {}))
        try:
            table = self.resource.Table(self.table_name)
            return table.item_count
        except Exception:
            return 0

    def get_original_items(self) -> list:
        items = self.scan_all()
        return [item for item in items if item.get("operation") == "original"]

    def get_processed_items(self) -> list:
        items = self.scan_all()
        return [item for item in items if item.get("status") == "processed" and item.get("operation") != "original"]

    def get_unique_product_names(self) -> list:
        items = self.scan_all()
        products = set()
        for item in items:
            if item.get("product_name"):
                products.add(item["product_name"])
        return list(products)

    def get_items_by_product(self, product_name: str) -> list:
        items = self.scan_all()
        return [item for item in items if item.get("product_name") == product_name]

    def query_by_parent_id(self, parent_id: str) -> list:
        items = self.scan_all()
        return [item for item in items if item.get("parent_id") == parent_id]
