import sys
import os
import io
import time
import json
from io import BytesIO

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

REPORT = []
PASS = 0
FAIL = 0


def test(name, fn):
    global PASS, FAIL
    print(f"\n{'='*60}\nTEST: {name}\n{'='*60}")
    try:
        result = fn()
        if result is False:
            print(f"[X] FAIL: {name}")
            REPORT.append(("FAIL", name, ""))
            FAIL += 1
            return False
        else:
            print(f"[OK] PASS: {name}")
            REPORT.append(("PASS", name, str(result) if not isinstance(result, bool) else ""))
            PASS += 1
            return True
    except Exception as e:
        import traceback
        print(f"[X] FAIL (Exception): {name}")
        print(traceback.format_exc())
        REPORT.append(("FAIL", name, str(e)))
        FAIL += 1
        return False


print("=" * 60)
print("MINI CLOUD IMAGE STUDIO - FEATURE TEST SUITE")
print("=" * 60)

# ----------------------------------------------------------------
# TEST 1: Imports & Configuration
# ----------------------------------------------------------------
def t_imports():
    from config.settings import settings
    from services.s3_service import S3Service
    from services.dynamodb_service import DynamoDBService
    from services.image_service import ImageService
    from utils.helpers import (
        generate_image_id, format_file_size, build_s3_key,
        get_current_timestamp, image_to_bytesio, sanitize_filename,
    )
    assert settings.S3_BUCKET_NAME == "mini-cloud-umkm-products"
    assert settings.DYNAMODB_TABLE_NAME == "umkm_product_images"
    assert settings.LOCALSTACK_ENDPOINT == "http://localhost:4566"
    return "OK"
test("Import Modules & Settings", t_imports)

# ----------------------------------------------------------------
# TEST 2: Helper functions
# ----------------------------------------------------------------
def t_helpers():
    from utils.helpers import (
        generate_image_id, format_file_size, build_s3_key,
        get_current_timestamp, sanitize_filename,
    )
    imgid = generate_image_id()
    assert imgid.startswith("IMG-") and len(imgid) == 13, f"Bad ID: {imgid}"
    assert format_file_size(2500000) == "2.38 MB"
    assert build_s3_key("original", "keripik.jpg") == "original/keripik.jpg"
    assert build_s3_key("processed", "keripik.jpg", "watermark") == "processed/keripik_watermark.jpg"
    assert sanitize_filename("FOTO PRODUK A.JPG") == "foto_produk_a.jpg"
    assert get_current_timestamp()
    return True
test("Utility Helpers Functions", t_helpers)

# ----------------------------------------------------------------
# TEST 3: Pillow Image Operations
# ----------------------------------------------------------------
def t_pillow():
    from PIL import Image
    from services.image_service import ImageService
    from utils.helpers import image_to_bytesio

    img = Image.new("RGB", (1920, 1080), color=(100, 200, 50))
    info = ImageService.get_image_info(img)
    assert info["width"] == 1920 and info["height"] == 1080
    assert info["mode"] == "RGB"

    resized = ImageService.resize_image(img, 1000)
    assert resized.width == 1000
    assert resized.height == int(1080 * 1000 / 1920)  # ratio preserved

    gray = ImageService.to_grayscale(img)
    assert gray.mode == "RGB"

    sepia = ImageService.to_sepia(img)
    assert sepia.mode == "RGB"
    px = sepia.getpixel((0, 0))
    assert px != (100, 200, 50), "Sepia should change pixel values"

    inv = ImageService.invert_colors(img)
    px2 = inv.convert("RGB").getpixel((0, 0))
    assert px2 == (255 - 100, 255 - 200, 255 - 50)

    for pos in ["bottom-right", "bottom-left", "top-right", "top-left", "center"]:
        wm = ImageService.add_watermark(img, "(c) UMKM Test", pos)
        assert wm.width == img.width

    # Convert formats
    for fmt in ["JPEG", "PNG", "WEBP"]:
        c_img, c_buf, c_fmt, c_ext, c_sz = ImageService.convert_format(img, fmt)
        assert c_fmt.upper() == fmt.upper()
        assert c_sz > 0
        assert len(c_buf.getvalue()) > 0

    buf = image_to_bytesio(img, "JPEG")
    assert len(buf.getvalue()) > 0
    return True
test("Pillow Image Operations (Resize/Grayscale/Sepia/Invert/Watermark/Convert)", t_pillow)

# ----------------------------------------------------------------
# TEST 4: LocalStack / S3 Connection
# ----------------------------------------------------------------
def t_s3_conn():
    from services.s3_service import S3Service
    s3 = S3Service()
    for _ in range(10):
        if s3.check_connection():
            break
        time.sleep(2)
    assert s3.check_connection(), "Cannot connect to LocalStack S3 endpoint"
    return True
test("S3 Connection to LocalStack (http://localhost:4566)", t_s3_conn)

# ----------------------------------------------------------------
# TEST 5: DynamoDB Connection
# ----------------------------------------------------------------
def t_ddb_conn():
    from services.dynamodb_service import DynamoDBService
    ddb = DynamoDBService()
    for _ in range(10):
        if ddb.check_connection():
            break
        time.sleep(2)
    assert ddb.check_connection(), "Cannot connect to LocalStack DynamoDB endpoint"
    return True
test("DynamoDB Connection to LocalStack (http://localhost:4566)", t_ddb_conn)

# ----------------------------------------------------------------
# TEST 6: S3 Bucket Creation
# ----------------------------------------------------------------
def t_s3_bucket():
    from services.s3_service import S3Service
    s3 = S3Service()
    ok = s3.ensure_bucket()
    assert ok, "Bucket not created"
    assert s3.bucket_exists(), "Bucket doesn't exist after ensure_bucket()"
    # Ensure idempotent
    ok2 = s3.ensure_bucket()
    assert ok2
    return True
test("S3 Ensure Bucket (create if missing)", t_s3_bucket)

# ----------------------------------------------------------------
# TEST 7: DynamoDB Table Creation
# ----------------------------------------------------------------
def t_ddb_table():
    from services.dynamodb_service import DynamoDBService
    ddb = DynamoDBService()
    ok = ddb.ensure_table()
    assert ok, "Table not created"
    assert ddb.table_exists(), "Table doesn't exist after ensure_table()"
    ok2 = ddb.ensure_table()
    assert ok2, "Idempotent ensure_table failed"
    return True
test("DynamoDB Ensure Table (create if missing, wait ACTIVE)", t_ddb_table)

# ----------------------------------------------------------------
# TEST 8: S3 Upload & Get Object
# ----------------------------------------------------------------
S3_TEST_KEY = None
def t_s3_upload_download():
    from services.s3_service import S3Service
    from services.image_service import ImageService
    from utils.helpers import image_to_bytesio
    from PIL import Image
    global S3_TEST_KEY

    s3 = S3Service()
    s3.ensure_bucket()

    img = Image.new("RGB", (800, 600), color="blue")
    buf = image_to_bytesio(img, "JPEG")
    S3_TEST_KEY = f"original/_TEST_{int(time.time())}.jpg"
    ok = s3.upload_fileobj(buf, S3_TEST_KEY, "image/jpeg")
    assert ok, "S3 upload_fileobj failed"

    # Download
    dl = s3.get_object(S3_TEST_KEY)
    assert dl is not None, "S3 get_object returned None"
    assert len(dl.getvalue()) > 0, "Downloaded object empty"

    # Size
    sz = s3.get_object_size(S3_TEST_KEY)
    assert sz > 0

    # List
    objects = s3.list_objects("original/")
    keys = [o["Key"] for o in objects]
    assert S3_TEST_KEY in keys, f"{S3_TEST_KEY} not in listing"

    # Count
    assert s3.count_objects() > 0
    return True
test("S3 Upload Object + Get Object + List Objects", t_s3_upload_download)

# ----------------------------------------------------------------
# TEST 9: DynamoDB Put/Get/Scan
# ----------------------------------------------------------------
TEST_IMG_ID = None
def t_ddb_crud():
    from services.dynamodb_service import DynamoDBService
    from utils.helpers import generate_image_id, get_current_timestamp
    global TEST_IMG_ID

    ddb = DynamoDBService()
    ddb.ensure_table()
    TEST_IMG_ID = generate_image_id()
    item = {
        "image_id": TEST_IMG_ID,
        "product_name": "TEST_Keripik",
        "category": "Makanan",
        "original_filename": "keripik.jpg",
        "processed_filename": f"{TEST_IMG_ID}.jpg",
        "s3_key": S3_TEST_KEY or f"original/{TEST_IMG_ID}.jpg",
        "upload_time": get_current_timestamp(),
        "file_size": 120000,
        "image_format": "JPEG",
        "width": 1920,
        "height": 1080,
        "operation": "original",
        "status": "uploaded",
        "parent_id": "-",
    }
    ok = ddb.put_item(item)
    assert ok, "put_item failed"

    fetched = ddb.get_item(TEST_IMG_ID)
    assert fetched is not None, "get_item returned None"
    assert fetched["product_name"] == "TEST_Keripik"
    assert fetched["operation"] == "original"

    # Scan
    items = ddb.scan_all()
    ids = [i["image_id"] for i in items]
    assert TEST_IMG_ID in ids, "Item not found in scan"
    assert len(ddb.get_unique_product_names()) > 0
    return True
test("DynamoDB Put Item + Get Item + Scan All", t_ddb_crud)

# ----------------------------------------------------------------
# TEST 10: Full Upload + Process + Save flow (simulate app)
# ----------------------------------------------------------------
FULL_IMG_ID = None
def t_full_workflow():
    from PIL import Image
    from services.s3_service import S3Service
    from services.dynamodb_service import DynamoDBService
    from services.image_service import ImageService
    from utils.helpers import (
        generate_image_id, get_current_timestamp, image_to_bytesio, build_s3_key,
    )
    global FULL_IMG_ID

    s3 = S3Service(); s3.ensure_bucket()
    ddb = DynamoDBService(); ddb.ensure_table()

    # Simulate user upload: original
    img = Image.new("RGB", (1600, 1200), (255, 150, 50))  # orange product photo
    FULL_IMG_ID = generate_image_id()
    orig_ext = "jpg"
    orig_s3_key = build_s3_key("original", f"{FULL_IMG_ID}.{orig_ext}")
    orig_buf = image_to_bytesio(img, "JPEG")
    orig_size = len(orig_buf.getvalue())
    assert s3.upload_fileobj(orig_buf, orig_s3_key, "image/jpeg")

    orig_meta = {
        "image_id": FULL_IMG_ID,
        "product_name": "Keripik Pisang Test",
        "category": "Makanan",
        "original_filename": "keripik_pisang.jpg",
        "processed_filename": f"{FULL_IMG_ID}.{orig_ext}",
        "s3_key": orig_s3_key,
        "upload_time": get_current_timestamp(),
        "file_size": orig_size,
        "image_format": "JPEG",
        "width": img.width,
        "height": img.height,
        "operation": "original",
        "status": "uploaded",
        "parent_id": "-",
    }
    assert ddb.put_item(orig_meta), "Original metadata save failed"

    # ----- Process operations -----
    operations = [
        ("resize", lambda: ImageService.resize_image(img, 800), f"resize_800"),
        ("grayscale", lambda: ImageService.to_grayscale(img), "grayscale"),
        ("sepia", lambda: ImageService.to_sepia(img), "sepia"),
        ("invert", lambda: ImageService.invert_colors(img), "invert"),
        ("watermark", lambda: ImageService.add_watermark(img, "(c) UMKM Test", "bottom-right"), "watermark"),
    ]
    fmt = "JPEG"
    for op_name, op_fn, suffix in operations:
        processed_img = op_fn()
        p_buf = image_to_bytesio(processed_img, fmt)
        p_key = build_s3_key("processed", f"{FULL_IMG_ID}.{orig_ext}", suffix)
        p_size = len(p_buf.getvalue())
        assert s3.upload_fileobj(p_buf, p_key, "image/jpeg"), f"S3 upload {op_name} failed"
        p_id = generate_image_id()
        p_meta = {
            "image_id": p_id,
            "product_name": "Keripik Pisang Test",
            "category": "Makanan",
            "original_filename": "keripik_pisang.jpg",
            "processed_filename": f"{FULL_IMG_ID}_{suffix}.{orig_ext}",
            "s3_key": p_key,
            "upload_time": get_current_timestamp(),
            "file_size": p_size,
            "image_format": fmt,
            "width": processed_img.width,
            "height": processed_img.height,
            "operation": op_name,
            "status": "processed",
            "parent_id": FULL_IMG_ID,
        }
        assert ddb.put_item(p_meta), f"DynamoDB {op_name} failed"

    # Convert Format: JPEG -> WEBP
    c_img, c_buf, c_fmt, c_ext, c_sz = ImageService.convert_format(img, "WEBP")
    c_suffix = f"to_{c_ext}"
    c_key = build_s3_key("processed", f"{FULL_IMG_ID}.{c_ext}", f"to_{c_ext}")
    assert s3.upload_fileobj(c_buf, c_key, "image/webp")
    c_id = generate_image_id()
    c_meta = {
        "image_id": c_id,
        "product_name": "Keripik Pisang Test",
        "category": "Makanan",
        "original_filename": "keripik_pisang.jpg",
        "processed_filename": f"{FULL_IMG_ID}_{c_suffix}.{c_ext}",
        "s3_key": c_key,
        "upload_time": get_current_timestamp(),
        "file_size": c_sz,
        "image_format": c_fmt,
        "width": c_img.width,
        "height": c_img.height,
        "operation": "convert format",
        "status": "processed",
        "parent_id": FULL_IMG_ID,
        "saved_size": orig_size - c_sz,
    }
    assert ddb.put_item(c_meta), "Convert save to DDB failed"
    assert c_sz > 0

    # ----- Validate counts -----
    originals = ddb.get_original_items()
    assert len([o for o in originals if o["product_name"] == "Keripik Pisang Test"]) >= 1
    processed = ddb.get_processed_items()
    assert len([p for p in processed if p["parent_id"] == FULL_IMG_ID]) >= 6  # 5 ops + convert
    s3_total = s3.get_total_storage()
    assert s3_total > 0, "Storage should be > 0"
    return f"OriginalID={FULL_IMG_ID}, TotalObjects={s3.count_objects()}, TotalStorage={s3_total} bytes"
test("Full Workflow: Upload + 6 Process Ops (Resize/GS/Sepia/Invert/WM/Convert) + Save S3 + DDB", t_full_workflow)

# ----------------------------------------------------------------
# TEST 11: Initialize App Services Function
# ----------------------------------------------------------------
def t_initialize_services():
    import app as appmod
    status = appmod.initialize_services()
    assert isinstance(status, dict)
    assert "localstack" in status
    assert "s3" in status
    assert "dynamodb" in status
    assert status["localstack"] == True, f"LocalStack status: {status}"
    assert status["s3"] == True
    assert status["dynamodb"] == True
    assert status["bucket_created"] == True
    assert status["table_created"] == True
    return True
test("initialize_services() from app.py (check+create bucket+table)", t_initialize_services)

# ----------------------------------------------------------------
# TEST 12: Dashboard Statistics Calculation
# ----------------------------------------------------------------
def t_dashboard_stats():
    from services.dynamodb_service import DynamoDBService
    from services.s3_service import S3Service
    s3 = S3Service()
    ddb = DynamoDBService()
    all_items = ddb.scan_all()
    original_items = [i for i in all_items if i.get("operation") == "original"]
    processed_items = [i for i in all_items if i.get("status") == "processed" and i.get("operation") != "original"]
    total_storage = s3.get_total_storage()
    unique_products = ddb.get_unique_product_names()
    assert len(all_items) > 0, "Expected items in DDB after workflow"
    assert len(original_items) >= 2
    assert len(processed_items) >= 6
    assert total_storage > 0
    assert len(unique_products) >= 2  # TEST_Keripik + Keripik Pisang Test
    return f"all={len(all_items)}, original={len(original_items)}, processed={len(processed_items)}, products={len(unique_products)}, storage={total_storage}"
test("Dashboard Statistics (counts, storage, unique products)", t_dashboard_stats)

# ----------------------------------------------------------------
# TEST 13: Delete Object + Item
# ----------------------------------------------------------------
def t_delete():
    from services.s3_service import S3Service
    from services.dynamodb_service import DynamoDBService
    s3 = S3Service(); s3.ensure_bucket()
    ddb = DynamoDBService(); ddb.ensure_table()

    # Upload a delete target
    from PIL import Image
    from utils.helpers import image_to_bytesio, generate_image_id, get_current_timestamp, build_s3_key
    img = Image.new("RGB", (100, 100), "red")
    buf = image_to_bytesio(img, "JPEG")
    did = generate_image_id()
    key = f"original/_DEL_{did}.jpg"
    assert s3.upload_fileobj(buf, key, "image/jpeg")
    meta = {"image_id": did, "product_name": "DELETE_ME", "s3_key": key,
            "upload_time": get_current_timestamp(), "file_size": len(buf.getvalue()),
            "operation": "original", "status": "uploaded", "parent_id": "-"}
    assert ddb.put_item(meta)

    # Delete from S3
    s3_del = s3.delete_object(key)
    assert s3_del
    assert s3.get_object(key) is None

    # Delete from DDB
    ddb_del = ddb.delete_item(did)
    assert ddb_del
    assert ddb.get_item(did) is None

    # Cleanup our test items
    if S3_TEST_KEY:
        s3.delete_object(S3_TEST_KEY)
    if TEST_IMG_ID:
        ddb.delete_item(TEST_IMG_ID)
    return f"Delete target cleaned up: {did}"
test("Delete from S3 + Delete from DynamoDB (rollback + cleanup test data)", t_delete)

# ----------------------------------------------------------------
# Print Report
# ----------------------------------------------------------------
print("\n" + "=" * 60)
print("TEST REPORT SUMMARY")
print("=" * 60)
print(f"Total : {len(REPORT)}")
print(f"PASS  : {PASS}")
print(f"FAIL  : {FAIL}")
print("=" * 60)
for status, name, detail in REPORT:
    mark = "[OK]" if status == "PASS" else "[X]"
    line = f"{mark} [{status}] {name}"
    if detail and detail != "True":
        line += f"  :: {detail[:80]}"
    print(line)

ts_fn = None
try:
    from utils.helpers import get_current_timestamp as _gts
    ts_fn = _gts
except Exception:
    pass

with open("TEST_REPORT.txt", "w", encoding="utf-8") as rf:
    rf.write("MINI CLOUD IMAGE STUDIO - TEST REPORT\n")
    rf.write(f"Generated: {ts_fn() if ts_fn else 'Now'}\n")
    rf.write(f"Total : {len(REPORT)} | PASS: {PASS} | FAIL: {FAIL}\n\n")
    for status, name, detail in REPORT:
        rf.write(f"[{status}] {name} {detail}\n")

sys.exit(0 if FAIL == 0 else 1)
