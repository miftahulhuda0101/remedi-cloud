import unittest
from io import BytesIO

from services.s3_service import S3Service
from services.dynamodb_service import DynamoDBService


class FallbackServicesTest(unittest.TestCase):
    def test_s3_fallback_upload_and_get(self):
        svc = S3Service()
        svc.client = None
        svc._use_fallback = True

        ok = svc.upload_fileobj(BytesIO(b"hello"), "original/test.txt", "text/plain")
        self.assertTrue(ok)

        obj = svc.get_object("original/test.txt")
        self.assertIsNotNone(obj)
        self.assertEqual(obj.read(), b"hello")

    def test_dynamodb_fallback_put_and_scan(self):
        svc = DynamoDBService()
        svc.client = None
        svc.resource = None
        svc._use_fallback = True

        ok = svc.put_item({"image_id": "img-1", "product_name": "Testing"})
        self.assertTrue(ok)

        items = svc.scan_all()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["image_id"], "img-1")


if __name__ == "__main__":
    unittest.main()
