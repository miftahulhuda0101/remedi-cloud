import streamlit as st
from io import BytesIO
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
from services.s3_service import S3Service
from services.dynamodb_service import DynamoDBService
from services.image_service import ImageService
from utils.helpers import (
    generate_image_id,
    get_current_timestamp,
    format_file_size,
    get_file_extension,
    build_s3_key,
    sanitize_filename,
    image_to_bytesio,
)


st.set_page_config(
    page_title="Mini Cloud Image Studio - UMKM",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def initialize_services():
    status = {
        "localstack": False,
        "s3": False,
        "dynamodb": False,
        "bucket_created": False,
        "table_created": False,
    }

    try:
        s3 = S3Service()
        status["localstack"] = s3.check_connection()
        if status["localstack"]:
            status["s3"] = s3.check_connection()
            bucket_exists = s3.bucket_exists()
            if not bucket_exists:
                status["bucket_created"] = s3.create_bucket()
            else:
                status["bucket_created"] = True
                status["s3"] = True

        dynamodb = DynamoDBService()
        if status["localstack"]:
            status["dynamodb"] = dynamodb.check_connection()
            table_exists = dynamodb.table_exists()
            if not table_exists:
                status["table_created"] = dynamodb.create_table()
            else:
                status["table_created"] = True
                status["dynamodb"] = True
    except Exception:
        pass

    return status


def get_content_type(filename: str) -> str:
    ext = get_file_extension(filename)
    content_map = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
    }
    return content_map.get(ext, "image/jpeg")


def status_indicator(label: str, ok: bool):
    color = "🟢" if ok else "🔴"
    text = "Connected" if ok else "Disconnected"
    return f"{color} **{label}**: {text}"


def main():
    if "services_initialized" not in st.session_state:
        with st.spinner("Initializing cloud services..."):
            init_status = initialize_services()
            st.session_state["services_initialized"] = True
            st.session_state["init_status"] = init_status

    try:
        s3_svc = S3Service()
        dynamo_svc = DynamoDBService()
    except Exception as e:
        st.error(f"Gagal menghubungkan ke LocalStack: {e}")
        st.warning("Pastikan Docker & LocalStack sudah berjalan (docker compose up -d)")
        return

    image_svc = ImageService()

    st.sidebar.title("📋 Menu Navigasi")
    menu = st.sidebar.radio(
        "Pilih Menu",
        [
            "🏠 Dashboard",
            "📤 Upload Product",
            "🎨 Image Editor",
            "🖼️ Product Gallery",
            "☁️ Cloud Storage",
        ],
        index=0,
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Status Koneksi")
    init_status = st.session_state.get("init_status", {})
    st.sidebar.markdown(status_indicator("LocalStack", init_status.get("localstack", False)))
    st.sidebar.markdown(status_indicator("S3", init_status.get("s3", False)))
    st.sidebar.markdown(status_indicator("DynamoDB", init_status.get("dynamodb", False)))

    if menu == "🏠 Dashboard":
        render_dashboard(s3_svc, dynamo_svc)
    elif menu == "📤 Upload Product":
        render_upload(s3_svc, dynamo_svc, image_svc)
    elif menu == "🎨 Image Editor":
        render_editor(s3_svc, dynamo_svc, image_svc)
    elif menu == "🖼️ Product Gallery":
        render_gallery(s3_svc, dynamo_svc)
    elif menu == "☁️ Cloud Storage":
        render_cloud_storage(s3_svc, dynamo_svc)


def render_dashboard(s3_svc: S3Service, dynamo_svc: DynamoDBService):
    st.title("🛍️ Mini Cloud Image Studio")
    st.subheader("Cloud-Based Image Processing untuk Foto Produk UMKM")
    st.markdown("---")

    try:
        all_items = dynamo_svc.scan_all()
        original_items = [i for i in all_items if i.get("operation") == "original"]
        processed_items = [i for i in all_items if i.get("status") == "processed" and i.get("operation") != "original"]
        total_images = len(all_items)
        total_storage = s3_svc.get_total_storage()
        unique_products = dynamo_svc.get_unique_product_names()
    except Exception:
        original_items = []
        processed_items = []
        total_images = 0
        total_storage = 0
        unique_products = []

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📦 Total Produk", len(unique_products), help="Jumlah produk UMKM yang berbeda")
    col2.metric("🖼️ Total Foto", total_images, help="Total seluruh foto (original + processed)")
    col3.metric("💾 Total Storage", format_file_size(total_storage), help="Kapasitas penyimpanan di S3")
    col4.metric("✨ Processed Images", len(processed_items), help="Foto yang telah melalui proses editing")

    st.markdown("---")
    st.subheader("📡 Connection Status")

    init_status = st.session_state.get("init_status", {})
    stat_cols = st.columns(3)
    stat_cols[0].info("**LocalStack**   🟢 Connected" if init_status.get("localstack") else "**LocalStack**   🔴 Disconnected")
    stat_cols[1].info("**S3**            🟢 Connected" if init_status.get("s3") else "**S3**            🔴 Disconnected")
    stat_cols[2].info("**DynamoDB**      🟢 Connected" if init_status.get("dynamodb") else "**DynamoDB**      🔴 Disconnected")

    st.markdown("---")
    st.subheader("📂 Informasi Bucket & Tabel")
    info_col1, info_col2 = st.columns(2)
    with info_col1:
        st.markdown(f"""
        **S3 Bucket**
        - Nama Bucket: `{settings.S3_BUCKET_NAME}`
        - Endpoint: `{settings.LOCALSTACK_ENDPOINT}`
        - Region: `{settings.AWS_REGION}`
        - Jumlah Object: {s3_svc.count_objects()}
        """)
    with info_col2:
        st.markdown(f"""
        **DynamoDB Table**
        - Nama Tabel: `{settings.DYNAMODB_TABLE_NAME}`
        - Primary Key: `image_id`
        - Jumlah Records: {dynamo_svc.count_items()}
        """)

    if original_items:
        st.markdown("---")
        st.subheader("📸 Produk Terbaru")
        latest = sorted(original_items, key=lambda x: x.get("upload_time", ""), reverse=True)[:6]
        cols = st.columns(3)
        for idx, item in enumerate(latest):
            with cols[idx % 3]:
                try:
                    s3_key = item.get("s3_key", "")
                    img_bytes = s3_svc.get_object(s3_key)
                    if img_bytes:
                        st.image(img_bytes, caption=item.get("product_name", ""), use_container_width=True)
                        st.caption(f"{item.get('image_format', '')} | {format_file_size(item.get('file_size', 0))}")
                except Exception:
                    pass


def render_upload(s3_svc: S3Service, dynamo_svc: DynamoDBService, image_svc: ImageService):
    st.title("📤 Upload Product")
    st.markdown("Upload foto produk UMKM ke Cloud Storage (S3) dan simpan metadata ke DynamoDB.")
    st.markdown("---")

    with st.form("upload_form", clear_on_submit=False):
        product_name = st.text_input("**Nama Produk**", placeholder="Contoh: Keripik Pisang")
        category = st.selectbox(
            "**Kategori Produk**",
            ["Makanan", "Minuman", "Fashion", "Kerajinan", "Kosmetik", "Elektronik", "Lainnya"],
            index=0,
        )
        uploaded_file = st.file_uploader(
            "**Upload Foto Produk**",
            type=["jpg", "jpeg", "png", "webp"],
            help="Format yang diperbolehkan: JPG, JPEG, PNG, WEBP",
        )
        submit = st.form_submit_button("🚀 Upload ke Cloud", type="primary")

    if submit:
        if not product_name.strip():
            st.error("❌ Nama produk tidak boleh kosong!")
        elif uploaded_file is None:
            st.error("❌ Silakan pilih file foto produk terlebih dahulu!")
        else:
            try:
                with st.spinner("Mengupload foto ke Cloud Storage..."):
                    file_bytes = uploaded_file.read()
                    file_size = len(file_bytes)
                    original_filename = sanitize_filename(uploaded_file.name)
                    ext = get_file_extension(original_filename)

                    try:
                        image = ImageService.open_image(BytesIO(file_bytes))
                    except Exception:
                        st.error("❌ File gambar corrupt atau format tidak didukung!")
                        return

                    info = ImageService.get_image_info(image)
                    image_id = generate_image_id()
                    s3_key = build_s3_key("original", f"{image_id}.{ext}")
                    content_type = get_content_type(original_filename)

                    upload_ok = s3_svc.upload_fileobj(BytesIO(file_bytes), s3_key, content_type)
                    if not upload_ok:
                        st.error("❌ Gagal mengupload ke S3. Cek koneksi LocalStack.")
                        return

                    metadata = {
                        "image_id": image_id,
                        "product_name": product_name.strip(),
                        "category": category,
                        "original_filename": original_filename,
                        "processed_filename": f"{image_id}.{ext}",
                        "s3_key": s3_key,
                        "upload_time": get_current_timestamp(),
                        "file_size": file_size,
                        "image_format": info["format"] or ext.upper(),
                        "width": info["width"],
                        "height": info["height"],
                        "operation": "original",
                        "status": "uploaded",
                        "parent_id": "-",
                    }
                    db_ok = dynamo_svc.put_item(metadata)
                    if not db_ok:
                        s3_svc.delete_object(s3_key)
                        st.error("❌ Gagal menyimpan metadata ke DynamoDB. Upload dibatalkan.")
                        return

                st.success("✅ Foto produk berhasil diupload ke Cloud Storage!")
                st.markdown("---")

                prev_col, info_col = st.columns([1, 1])
                with prev_col:
                    st.markdown("### 📷 Preview")
                    st.image(file_bytes, caption=f"Preview: {product_name}", use_container_width=True)
                with info_col:
                    st.markdown("### 📋 Informasi File")
                    st.markdown(f"""
                    - **Image ID**: `{image_id}`
                    - **Nama Produk**: {product_name}
                    - **Kategori**: {category}
                    - **Original Filename**: `{original_filename}`
                    - **S3 Key**: `{s3_key}`
                    - **Ukuran File**: {format_file_size(file_size)}
                    - **Format**: {info['format'] or ext.upper()}
                    - **Dimensi**: {info['width']} x {info['height']} px
                    - **Waktu Upload**: {metadata['upload_time']}
                    """)

                    st.markdown("### 📡 Metadata DynamoDB")
                    st.json(metadata, expanded=False)
            except Exception as e:
                st.error(f"❌ Terjadi kesalahan saat upload: {e}")

    if uploaded_file is not None and not submit:
        try:
            file_bytes = uploaded_file.read()
            image = ImageService.open_image(BytesIO(file_bytes))
            info = ImageService.get_image_info(image)
            st.markdown("---")
            st.subheader("🔍 Preview Sebelum Upload")
            pc, ic = st.columns([1, 1])
            with pc:
                st.image(file_bytes, caption="Preview Gambar", use_container_width=True)
            with ic:
                st.markdown(f"""
                - **Nama File**: `{uploaded_file.name}`
                - **Ukuran File**: {format_file_size(len(file_bytes))}
                - **Format**: {info['format']}
                - **Dimensi**: {info['width']} x {info['height']} px
                - **Mode**: {info['mode']}
                """)
        except Exception as e:
            st.warning(f"Tidak dapat menampilkan preview: {e}")


def render_editor(s3_svc: S3Service, dynamo_svc: DynamoDBService, image_svc: ImageService):
    st.title("🎨 Image Editor")
    st.markdown("Edit foto produk: Resize, Grayscale, Sepia, Invert, Watermark, Convert Format")
    st.markdown("---")

    try:
        original_items = dynamo_svc.get_original_items()
    except Exception:
        original_items = []

    if not original_items:
        st.warning("⚠️ Belum ada foto produk yang diupload. Silakan upload terlebih dahulu di menu Upload Product.")
        return

    product_options = {}
    for item in original_items:
        label = f"{item.get('product_name', 'Unknown')} [{item.get('image_id', '')}]"
        product_options[label] = item

    selected_label = st.selectbox(
        "**Pilih Foto Produk**",
        list(product_options.keys()),
        index=0,
        key="editor_select",
    )
    selected = product_options[selected_label]

    try:
        s3_key = selected.get("s3_key", "")
        img_bytes = s3_svc.get_object(s3_key)
        if not img_bytes:
            st.error("❌ File tidak ditemukan di S3.")
            return
        original_image = image_svc.open_image(img_bytes)
        img_bytes.seek(0)
    except Exception as e:
        st.error(f"❌ Gagal memuat gambar dari S3: {e}")
        return

    st.markdown("### 🖼️ Original Image")
    orig_col, meta_col = st.columns([2, 1])
    with orig_col:
        st.image(img_bytes.getvalue(), caption=f"{selected.get('product_name')}", use_container_width=True)
    with meta_col:
        st.markdown(f"""
        - **Image ID**: `{selected.get('image_id')}`
        - **Nama**: {selected.get('product_name')}
        - **Format**: {selected.get('image_format')}
        - **Ukuran**: {format_file_size(selected.get('file_size', 0))}
        - **Dimensi**: {selected.get('width')} x {selected.get('height')} px
        """)

    st.markdown("---")
    st.subheader("⚙️ Pilih Operasi")
    operation = st.radio(
        "Jenis Operasi",
        ["Original", "Resize", "Grayscale", "Sepia", "Invert", "Watermark", "Convert Format"],
        index=0,
        horizontal=True,
    )

    processed_image = None
    processed_buf = None
    result_format = selected.get("image_format", "JPEG")
    new_ext = get_file_extension(selected.get("processed_filename", "img.jpg"))
    new_size = 0
    op_suffix = ""
    extra_info = {}

    if operation == "Original":
        processed_image = original_image.copy()
        processed_buf = img_bytes
        result_format = selected.get("image_format", "JPEG")
        new_size = selected.get("file_size", 0)
        op_suffix = "original"

    elif operation == "Resize":
        st.markdown("#### 📐 Resize Configuration")
        orig_w = selected.get("width", 1000)
        orig_h = selected.get("height", 1000)
        target_w = st.slider(
            f"Lebar Gambar (Original: {orig_w} x {orig_h})",
            min_value=100,
            max_value=max(orig_w, 1000),
            value=min(1000, orig_w),
            step=50,
            key="resize_slider",
        )
        ratio = target_w / orig_w
        target_h = int(orig_h * ratio)
        st.caption(f"Resize: **{target_w}** x **{target_h}** px | Ratio dipertahankan otomatis")

        if st.button("🔄 Apply Resize", type="primary", key="btn_resize"):
            with st.spinner("Memproses resize..."):
                processed_image = image_svc.resize_image(original_image, target_w)
                processed_buf = image_to_bytesio(processed_image, selected.get("image_format", "JPEG"))
                result_format = selected.get("image_format", "JPEG")
                new_size = len(processed_buf.getvalue())
                op_suffix = f"resize_{target_w}"
                extra_info = {"new_width": target_w, "new_height": target_h}

    elif operation == "Grayscale":
        if st.button("⚫ Apply Grayscale", type="primary", key="btn_gray"):
            with st.spinner("Mengubah ke Grayscale..."):
                processed_image = image_svc.to_grayscale(original_image)
                processed_buf = image_to_bytesio(processed_image, selected.get("image_format", "JPEG"))
                result_format = selected.get("image_format", "JPEG")
                new_size = len(processed_buf.getvalue())
                op_suffix = "grayscale"

    elif operation == "Sepia":
        if st.button("🟤 Apply Sepia", type="primary", key="btn_sepia"):
            with st.spinner("Menerapkan filter Sepia..."):
                processed_image = image_svc.to_sepia(original_image)
                processed_buf = image_to_bytesio(processed_image, selected.get("image_format", "JPEG"))
                result_format = selected.get("image_format", "JPEG")
                new_size = len(processed_buf.getvalue())
                op_suffix = "sepia"

    elif operation == "Invert":
        if st.button("🔵 Apply Invert Color", type="primary", key="btn_invert"):
            with st.spinner("Membalik warna gambar..."):
                processed_image = image_svc.invert_colors(original_image)
                processed_buf = image_to_bytesio(processed_image, selected.get("image_format", "JPEG"))
                result_format = selected.get("image_format", "JPEG")
                new_size = len(processed_buf.getvalue())
                op_suffix = "invert"

    elif operation == "Watermark":
        st.markdown("#### 💧 Watermark Configuration")
        umkm_name = st.text_input("Nama UMKM", value="UMKM Anda", key="wm_name")
        default_wm = f"© {umkm_name}" if umkm_name != "UMKM Anda" else settings.DEFAULT_WATERMARK
        wm_text = st.text_input("Teks Watermark", value=default_wm, key="wm_text")
        wm_position = st.selectbox(
            "Posisi Watermark",
            ["Bottom Right", "Bottom Left", "Top Right", "Top Left", "Center"],
            index=0,
            key="wm_pos",
        )
        pos_map = {
            "Bottom Right": "bottom-right",
            "Bottom Left": "bottom-left",
            "Top Right": "top-right",
            "Top Left": "top-left",
            "Center": "center",
        }

        if st.button("💧 Apply Watermark", type="primary", key="btn_wm"):
            with st.spinner("Menambahkan watermark..."):
                processed_image = image_svc.add_watermark(
                    original_image,
                    wm_text,
                    position=pos_map.get(wm_position, "bottom-right"),
                )
                processed_buf = image_to_bytesio(processed_image, selected.get("image_format", "JPEG"))
                result_format = selected.get("image_format", "JPEG")
                new_size = len(processed_buf.getvalue())
                op_suffix = "watermark"
                extra_info = {"watermark_text": wm_text, "watermark_position": wm_position}

    elif operation == "Convert Format":
        st.markdown("#### 🔁 Convert Format")
        orig_fmt = selected.get("image_format", "JPEG")
        orig_size = selected.get("file_size", 0)
        st.caption(f"Original Format: **{orig_fmt}** | Original Size: **{format_file_size(orig_size)}**")

        target_format = st.selectbox(
            "Convert To",
            ["JPEG", "PNG", "WEBP"],
            index=2,
            key="conv_format",
        )
        if st.button("🔁 Convert", type="primary", key="btn_conv"):
            with st.spinner(f"Converting ke {target_format}..."):
                processed_image, processed_buf, result_format, new_ext, new_size = image_svc.convert_format(
                    original_image, target_format
                )
                op_suffix = f"to_{new_ext}"
                saved = orig_size - new_size
                extra_info = {"original_size": orig_size, "new_size": new_size, "saved_size": saved}

    if processed_image is not None and processed_buf is not None:
        st.markdown("---")
        st.subheader("📊 Hasil Proses")
        ocol, pcol = st.columns(2)
        with ocol:
            st.markdown("**Original Image**")
            st.image(img_bytes.getvalue(), caption=f"Original", use_container_width=True)
        with pcol:
            st.markdown(f"**Processed Image ({operation})**")
            st.image(processed_buf.getvalue(), caption=f"{operation}", use_container_width=True)

        st.markdown("---")
        info_col1, info_col2, info_col3 = st.columns(3)
        info_col1.metric("Format", result_format)
        info_col2.metric("Dimensi", f"{processed_image.width} x {processed_image.height}")
        info_col3.metric("Ukuran File", format_file_size(new_size))

        if operation == "Convert Format" and extra_info:
            saved = extra_info.get("saved_size", 0)
            delta_saved = f"Hemat {format_file_size(saved)}" if saved > 0 else f"Tambah {format_file_size(abs(saved))}"
            st.info(f"📊 Original Size : {format_file_size(selected.get('file_size', 0))}  |  New Size: {format_file_size(new_size)}  |  Saved: {delta_saved}")

        st.markdown("---")
        btn_col1, btn_col2 = st.columns(2)

        with btn_col1:
            if st.button("💾 Save to S3", type="primary", key="btn_save_s3", use_container_width=True):
                with st.spinner("Menyimpan hasil ke S3 dan DynamoDB..."):
                    try:
                        if operation == "Convert Format":
                            proc_filename = f"{selected.get('image_id')}_{op_suffix}.{new_ext}"
                        else:
                            proc_filename = f"{selected.get('image_id')}_{op_suffix}.{new_ext}"
                        new_s3_key = build_s3_key("processed", proc_filename)
                        content_type = get_content_type(proc_filename)

                        processed_buf.seek(0)
                        ok = s3_svc.upload_fileobj(processed_buf, new_s3_key, content_type)
                        if not ok:
                            st.error("❌ Gagal menyimpan ke S3")
                        else:
                            new_image_id = generate_image_id()
                            new_metadata = {
                                "image_id": new_image_id,
                                "product_name": selected.get("product_name"),
                                "category": selected.get("category", "-"),
                                "original_filename": selected.get("original_filename"),
                                "processed_filename": proc_filename,
                                "s3_key": new_s3_key,
                                "upload_time": get_current_timestamp(),
                                "file_size": new_size,
                                "image_format": result_format,
                                "width": processed_image.width,
                                "height": processed_image.height,
                                "operation": operation.lower(),
                                "status": "processed",
                                "parent_id": selected.get("image_id"),
                            }
                            if extra_info:
                                for k, v in extra_info.items():
                                    new_metadata[k] = str(v)

                            db_ok = dynamo_svc.put_item(new_metadata)
                            if db_ok:
                                st.success(f"✅ Berhasil disimpan ke S3! Image ID: `{new_image_id}`")
                                st.caption(f"S3 Key: `{new_s3_key}`")
                            else:
                                s3_svc.delete_object(new_s3_key)
                                st.error("❌ Gagal menyimpan metadata ke DynamoDB")
                    except Exception as e:
                        st.error(f"❌ Terjadi kesalahan: {e}")

        with btn_col2:
            processed_buf.seek(0)
            download_name = f"{selected.get('product_name').replace(' ', '_')}_{op_suffix}.{new_ext}"
            st.download_button(
                "⬇️ Download Hasil",
                data=processed_buf.getvalue(),
                file_name=download_name,
                mime=get_content_type(download_name),
                use_container_width=True,
                key="btn_download_proc",
            )


def render_gallery(s3_svc: S3Service, dynamo_svc: DynamoDBService):
    st.title("🖼️ Product Gallery")
    st.markdown("Galeri foto produk UMKM dari DynamoDB & S3")
    st.markdown("---")

    try:
        all_items = dynamo_svc.scan_all()
    except Exception:
        all_items = []

    if not all_items:
        st.warning("⚠️ Belum ada data produk. Upload terlebih dahulu di menu Upload Product.")
        return

    filter_op = st.multiselect(
        "Filter berdasarkan Operasi",
        ["original", "resize", "grayscale", "sepia", "invert", "watermark", "convert format"],
        default=["original"],
    )
    if filter_op:
        all_items = [i for i in all_items if i.get("operation", "").lower() in [f.lower() for f in filter_op]]

    if not all_items:
        st.warning("⚠️ Tidak ada item sesuai filter.")
        return

    all_items = sorted(all_items, key=lambda x: x.get("upload_time", ""), reverse=True)

    COLS = 3
    for i in range(0, len(all_items), COLS):
        cols = st.columns(COLS)
        for j in range(COLS):
            idx = i + j
            if idx >= len(all_items):
                continue
            item = all_items[idx]
            with cols[j]:
                with st.container(border=True):
                    try:
                        s3_key = item.get("s3_key", "")
                        img_bytes = s3_svc.get_object(s3_key)
                        if img_bytes:
                            st.image(img_bytes.getvalue(), use_container_width=True)
                        else:
                            st.warning("Gambar tidak tersedia")
                    except Exception:
                        st.warning("Gagal memuat gambar")

                    st.markdown(f"**{item.get('product_name', 'Unknown')}**")
                    op = item.get("operation", "-")
                    status = item.get("status", "-")
                    st.caption(f"ID: `{item.get('image_id')}` | {op} | {status}")
                    st.caption(f"{item.get('image_format', '')} | {format_file_size(item.get('file_size', 0))} | {item.get('width', 0)}x{item.get('height', 0)}")
                    st.caption(f"📅 {item.get('upload_time', '')}")

                    b1, b2, b3 = st.columns(3)

                    view_key = f"view_{item.get('image_id')}"
                    dl_key = f"dl_{item.get('image_id')}"
                    del_key = f"del_{item.get('image_id')}"

                    with b1:
                        if st.button("🔍 View", key=view_key, use_container_width=True):
                            st.session_state["view_item"] = item
                    with b2:
                        try:
                            s3_key = item.get("s3_key", "")
                            dl_bytes = s3_svc.get_object(s3_key)
                            if dl_bytes:
                                dl_bytes.seek(0)
                                st.download_button(
                                    "⬇️",
                                    data=dl_bytes.getvalue(),
                                    file_name=item.get("processed_filename", f"{item.get('image_id')}.jpg"),
                                    mime=get_content_type(item.get("processed_filename", "img.jpg")),
                                    key=dl_key,
                                    use_container_width=True,
                                )
                        except Exception:
                            st.button("⬇️", disabled=True, key=dl_key, use_container_width=True)
                    with b3:
                        if st.button("🗑️", key=del_key, use_container_width=True):
                            st.session_state[f"confirm_delete_{item.get('image_id')}"] = True

    if "view_item" in st.session_state:
        item = st.session_state["view_item"]
        with st.expander(f"🔍 Detail: {item.get('product_name')} - {item.get('image_id')}", expanded=True):
            dcol1, dcol2 = st.columns([1, 1])
            try:
                s3_key = item.get("s3_key", "")
                detail_bytes = s3_svc.get_object(s3_key)
                if detail_bytes:
                    dcol1.image(detail_bytes.getvalue(), caption="Full Size", use_container_width=True)
            except Exception:
                dcol1.warning("Gagal memuat gambar")
            dcol2.json(item, expanded=True)
            if st.button("Close", key="close_view"):
                st.session_state.pop("view_item", None)
                st.rerun()

    for item in all_items:
        confirm_key = f"confirm_delete_{item.get('image_id')}"
        if st.session_state.get(confirm_key, False):
            with st.container(border=True):
                st.error(f"⚠️ Konfirmasi Hapus: **{item.get('product_name')}** (`{item.get('image_id')}`)")
                st.warning("File di S3 dan metadata di DynamoDB akan dihapus permanen!")
                c1, c2 = st.columns(2)
                if c1.button("✅ Ya, Hapus Permanen", key=f"confirm_yes_{item.get('image_id')}", type="primary"):
                    try:
                        s3_ok = s3_svc.delete_object(item.get("s3_key", ""))
                        db_ok = dynamo_svc.delete_item(item.get("image_id"))
                        if s3_ok and db_ok:
                            st.success(f"✅ Foto `{item.get('image_id')}` berhasil dihapus.")
                        else:
                            st.error("❌ Sebagian data gagal dihapus.")
                    except Exception as e:
                        st.error(f"❌ Gagal menghapus: {e}")
                    st.session_state.pop(confirm_key, None)
                    time_exists = __import__("time")
                    time_exists.sleep(1)
                    st.rerun()
                if c2.button("❌ Batal", key=f"confirm_no_{item.get('image_id')}"):
                    st.session_state.pop(confirm_key, None)
                    st.rerun()


def render_cloud_storage(s3_svc: S3Service, dynamo_svc: DynamoDBService):
    st.title("☁️ Cloud Storage")
    st.markdown("Informasi dan monitoring AWS S3 + DynamoDB di LocalStack")
    st.markdown("---")

    try:
        total_objects = s3_svc.count_objects()
        total_storage = s3_svc.get_total_storage()
        total_records = dynamo_svc.count_items()
        objects = s3_svc.list_objects()
        records = dynamo_svc.scan_all()
    except Exception:
        total_objects = 0
        total_storage = 0
        total_records = 0
        objects = []
        records = []

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🪣 S3 Bucket", settings.S3_BUCKET_NAME)
    m2.metric("📦 Objects", total_objects)
    m3.metric("💾 Storage Used", format_file_size(total_storage))
    m4.metric("📋 DynamoDB Records", total_records)

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🪣 S3 Bucket Information")
        st.markdown(f"""
        | Property | Value |
        |---|---|
        | Bucket Name | `{settings.S3_BUCKET_NAME}` |
        | Endpoint | `{settings.LOCALSTACK_ENDPOINT}` |
        | Region | `{settings.AWS_REGION}` |
        | Total Objects | **{total_objects}** |
        | Storage Used | **{format_file_size(total_storage)}** |
        """)

        original_count = s3_svc.count_by_prefix("original/")
        processed_count = s3_svc.count_by_prefix("processed/")
        thumbnail_count = s3_svc.count_by_prefix("thumbnail/")
        st.markdown("**Object Distribution by Folder**")
        st.markdown(f"- 📁 original/: **{original_count}** object")
        st.markdown(f"- 📁 processed/: **{processed_count}** object")
        st.markdown(f"- 📁 thumbnail/: **{thumbnail_count}** object")

    with c2:
        st.subheader("📋 DynamoDB Table Information")
        st.markdown(f"""
        | Property | Value |
        |---|---|
        | Table Name | `{settings.DYNAMODB_TABLE_NAME}` |
        | Primary Key | `image_id` (HASH) |
        | Region | `{settings.AWS_REGION}` |
        | Total Records | **{total_records}** |
        """)

        op_count = {}
        for r in records:
            op = r.get("operation", "unknown")
            op_count[op] = op_count.get(op, 0) + 1
        st.markdown("**Records by Operation**")
        for op, cnt in sorted(op_count.items()):
            st.markdown(f"- ⚙️ {op}: **{cnt}** record")

    st.markdown("---")
    st.subheader("📂 Daftar Object S3")
    if objects:
        obj_data = []
        for obj in objects:
            key = obj.get("Key", "")
            size = obj.get("Size", 0)
            last_mod = obj.get("LastModified", "-")
            obj_data.append({
                "Object Key": key,
                "Size": format_file_size(size),
                "Last Modified": str(last_mod),
                "Folder": key.split("/")[0] if "/" in key else "-",
            })
        st.dataframe(obj_data, use_container_width=True, hide_index=True)
    else:
        st.info("📭 Bucket kosong atau tidak terhubung.")

    st.markdown("---")
    st.subheader("📋 Daftar Records DynamoDB")
    if records:
        records_sorted = sorted(records, key=lambda x: x.get("upload_time", ""), reverse=True)
        st.dataframe(records_sorted, use_container_width=True, hide_index=True)
    else:
        st.info("📭 Tabel DynamoDB kosong atau tidak terhubung.")


if __name__ == "__main__":
    main()
