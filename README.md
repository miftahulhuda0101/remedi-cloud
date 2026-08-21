# 🛍️ Mini Cloud Image Studio – UMKM Product Photo

> Aplikasi Cloud Computing berbasis Python untuk upload, menyimpan, mengedit, dan mengelola foto produk UMKM menggunakan **AWS S3 & DynamoDB** yang di-simulasikan secara lokal melalui **LocalStack**.

---

## 📋 Deskripsi Aplikasi

Mini Cloud Image Studio adalah aplikasi web yang dirancang khusus untuk membantu pemilik UMKM dalam mengelola foto produk sebelum digunakan di marketplace atau media sosial. Aplikasi ini menawarkan fitur-fitur pengolahan gambar profesional seperti resize, grayscale, sepia, invert color, watermark branding, dan format converter — semuanya berjalan di atas arsitektur cloud lokal menggunakan LocalStack.

**Target Pengguna:** Pemilik UMKM, Admin Marketplace, Content Creator UMKM

---

## 🏗️ Arsitektur Aplikasi

```
Pemilik UMKM (User)
        ↓
    🌐 Streamlit (User Interface)
        ↓
    🐍 Python + Boto3 (AWS SDK)
        ↓
    🐳 LocalStack (AWS Cloud Simulation)
        ├─ 🪣 Amazon S3 (Penyimpanan foto)
        └─ 🗄️ Amazon DynamoDB (Metadata foto)
        ↓
    🖼️ Pillow / PIL (Manipulasi gambar)
```

**Alur Data:**
1. User upload foto melalui Streamlit UI
2. Aplikasi memvalidasi & menampilkan preview gambar menggunakan Pillow
3. Foto original disimpan ke **S3 Bucket** (`original/`)
4. Metadata (image_id, nama produk, ukuran, dll) disimpan ke **DynamoDB Table**
5. User memilih operasi edit (Resize/Grayscale/Sepia/dll)
6. Pemrosesan gambar dilakukan oleh **Pillow** di memori
7. Hasil edit disimpan kembali ke S3 (`processed/`)
8. Metadata proses edit disimpan ke DynamoDB dengan `parent_id` merujuk ke foto original

---

## 🛠️ Teknologi yang Digunakan

| Teknologi | Versi | Fungsi |
|---|---|---|
| **Python 3** | 3.8+ | Bahasa pemrograman utama |
| **Streamlit** | Terbaru | Frontend / User Interface |
| **Boto3** | Terbaru | AWS SDK untuk komunikasi dengan S3 & DynamoDB |
| **Pillow / PIL** | Terbaru | Library manipulasi & editing gambar |
| **LocalStack** | Latest (Docker) | Simulasi AWS Cloud secara lokal |
| **Amazon S3** | Simulasi | Object Storage untuk file foto |
| **Amazon DynamoDB** | Simulasi | NoSQL Database untuk metadata |
| **Docker Compose** | 3.8+ | Container orchestration LocalStack |
| **python-dotenv** | Terbaru | Load environment variables |

---

## 📦 Struktur Project

```
mini-cloud-image-studio/
│
├── app.py                          # Main Streamlit Application (UI)
├── requirements.txt                # Python dependencies
├── docker-compose.yml              # LocalStack Docker configuration
├── .env                            # Environment variables (aktif)
├── .env.example                    # Template environment variables
├── README.md                       # Dokumentasi ini
│
├── config/                         # ⚙️ KONFIGURASI
│   ├── __init__.py
│   └── settings.py                 # Load .env & settings Boto3
│
├── services/                       # 📡 LAYANAN CLOUD
│   ├── __init__.py
│   ├── s3_service.py               # S3: Upload, Download, Delete, List
│   ├── dynamodb_service.py         # DynamoDB: CRUD metadata
│   └── image_service.py            # Pillow: Resize/Grayscale/Sepia/Invert/Watermark/Convert
│
└── utils/                          # 🔧 UTILITAS
    ├── __init__.py
    └── helpers.py                  # Helper functions (ID, timestamp, format size, dll)
```

---

## 🚀 Instalasi & Menjalankan Aplikasi

### 1. Prasyarat

Pastikan software berikut sudah terinstall di komputer Anda:
- ✅ **Python 3.8** atau lebih baru
- ✅ **Docker Desktop** (untuk menjalankan LocalStack)
- ✅ **Pip** (package manager Python)

### 2. Clone / Download Project

```bash
cd mini-cloud-image-studio
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

Isi dari **requirements.txt**:
```
streamlit
boto3
Pillow
python-dotenv
```

### 4. Jalankan LocalStack via Docker

```bash
docker compose up -d
```

Tunggu beberapa saat sampai LocalStack siap (±30-60 detik).

**Service LocalStack yang aktif:**
- S3 endpoint: `http://localhost:4566`
- DynamoDB endpoint: `http://localhost:4566`

### 5. Konfigurasi Environment (.env)

File **.env** sudah disiapkan default:
```env
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_REGION=us-east-1
LOCALSTACK_ENDPOINT=http://localhost:4566
S3_BUCKET_NAME=mini-cloud-umkm-products
DYNAMODB_TABLE_NAME=umkm_product_images
```

### 6. Jalankan Aplikasi Streamlit

```bash
streamlit run app.py
```

Aplikasi akan terbuka otomatis di browser:
- **URL:** `http://localhost:8501`

✅ **Auto Initialization:** Saat pertama kali dijalankan, aplikasi otomatis:
1. Mengecek koneksi LocalStack
2. Membuat bucket S3 `mini-cloud-umkm-products` (jika belum ada)
3. Membuat tabel DynamoDB `umkm_product_images` (jika belum ada)
4. Menunggu tabel DynamoDB menjadi ACTIVE
5. Menampilkan status koneksi di Sidebar

---

## ✅ Cara Mengecek Service AWS

### Mengecek S3 Bucket & Objects

Gunakan **AWS CLI** dengan endpoint LocalStack:

```bash
# List semua bucket
aws --endpoint-url=http://localhost:4566 s3 ls

# List object di bucket mini-cloud-umkm-products
aws --endpoint-url=http://localhost:4566 s3 ls s3://mini-cloud-umkm-products --recursive

# Lihat struktur folder
aws --endpoint-url=http://localhost:4566 s3 ls s3://mini-cloud-umkm-products/original/
aws --endpoint-url=http://localhost:4566 s3 ls s3://mini-cloud-umkm-products/processed/
```

### Mengecek DynamoDB Table

```bash
# List semua tabel
aws --endpoint-url=http://localhost:4566 dynamodb list-tables

# Deskripsi tabel
aws --endpoint-url=http://localhost:4566 dynamodb describe-table --table-name umkm_product_images

# Scan semua records
aws --endpoint-url=http://localhost:4566 dynamodb scan --table-name umkm_product_images
```

---

## 📖 Cara Menggunakan Aplikasi

### 🏠 Halaman 1: Dashboard
- Melihat **4 Metric Utama**: Total Produk, Total Foto, Total Storage, Processed Images
- Status koneksi **LocalStack / S3 / DynamoDB** (🟢 Connected / 🔴 Disconnected)
- Informasi Bucket & Tabel
- Preview 6 produk terbaru

### 📤 Halaman 2: Upload Product
1. Isi **Nama Produk** (contoh: Keripik Pisang)
2. Pilih **Kategori** (Makanan/Minuman/Fashion/dll)
3. Klik **Browse Files** → pilih foto produk (JPG/JPEG/PNG/WEBP)
4. Aplikasi menampilkan **preview + informasi file**
5. Klik tombol **🚀 Upload ke Cloud**
6. ✅ Notifikasi sukses + metadata tersimpan

### 🎨 Halaman 3: Image Editor (7 Fitur)
1. **Pilih foto** dari dropdown produk yang sudah diupload
2. Pilih jenis operasi:

| Operasi | Cara Kerja |
|---|---|
| **Original** | Menampilkan gambar asli tanpa perubahan |
| **Resize** | Slider untuk lebar (width) → aspect ratio otomatis dipertahankan |
| **Grayscale** | Ubah gambar jadi hitam putih (ImageOps.grayscale) |
| **Sepia** | Filter warna kecoklatan khas foto lama (pixel-by-pixel transform) |
| **Invert** | Balik warna gambar (ImageOps.invert) |
| **Watermark** | Tambah teks © Nama UMKM dengan 5 pilihan posisi |
| **Convert Format** | Konversi JPEG ↔ PNG ↔ WEBP, menampilkan penghematan size |

3. Klik tombol **Apply** untuk preview hasil
4. Pilih:
   - 💾 **Save to S3** → simpan hasil ke folder `processed/` + metadata ke DynamoDB
   - ⬇️ **Download Hasil** → download ke komputer lokal

### 🖼️ Halaman 4: Product Gallery
- Menampilkan **grid foto produk** (3 kolom)
- **Filter** berdasarkan operasi (original/resize/grayscale/dll)
- Setiap card memiliki 3 tombol:
  - 🔍 **View** → lihat detail gambar & JSON metadata
  - ⬇️ **Download** → download file
  - 🗑️ **Delete** → hapus dari S3 + DynamoDB (dengan konfirmasi)

### ☁️ Halaman 5: Cloud Storage
- **Metric S3**: Bucket Name, Objects, Storage Used, DynamoDB Records
- **Table S3**: Daftar semua object (Key, Size, Last Modified, Folder)
- **Table DynamoDB**: Daftar semua metadata record

---

## 🔌 Penjelasan Integrasi Boto3

### Konfigurasi Boto3 (Universal)

Semua koneksi Boto3 diarahkan ke **LocalStack** (bukan AWS asli):

**S3 Client (di `services/s3_service.py`):**
```python
self.client = boto3.client(
    "s3",
    endpoint_url="http://localhost:4566",  # ← LocalStack
    aws_access_key_id="test",
    aws_secret_access_key="test",
    region_name="us-east-1",
)
```

**DynamoDB Resource (di `services/dynamodb_service.py`):**
```python
self.resource = boto3.resource(
    "dynamodb",
    endpoint_url="http://localhost:4566",  # ← LocalStack
    aws_access_key_id="test",
    aws_secret_access_key="test",
    region_name="us-east-1",
)
```

### Struktur Object Key di S3

| Folder | Contoh Key | Keterangan |
|---|---|---|
| `original/` | `original/IMG-12345678.jpg` | Foto asli hasil upload |
| `processed/` | `processed/IMG-12345678_resize_1000.jpg` | Hasil edit |
| `processed/` | `processed/IMG-12345678_watermark.jpg` | Foto dengan watermark |
| `processed/` | `processed/IMG-12345678_to_webp.webp` | Hasil format convert |

### Struktur Record di DynamoDB

| Field | Type | Contoh | Keterangan |
|---|---|---|---|
| `image_id` (PK) | String | `IMG-A1B2C3D4` | Primary Key unik |
| `product_name` | String | `Keripik Pisang` | Nama produk |
| `category` | String | `Makanan` | Kategori produk |
| `original_filename` | String | `keripik.jpg` | Nama file asli upload |
| `processed_filename` | String | `IMG-A1B2C3D4.jpg` | Nama file di S3 |
| `s3_key` | String | `original/IMG-A1B2C3D4.jpg` | Path object di S3 |
| `upload_time` | String | `2026-08-20 14:30:00` | Waktu upload |
| `file_size` | Number | `2400000` | Ukuran dalam bytes |
| `image_format` | String | `JPEG` | Format/tipe gambar |
| `width` | Number | `1920` | Lebar pixel |
| `height` | Number | `1080` | Tinggi pixel |
| `operation` | String | `original` / `resize` / `watermark` | Jenis operasi |
| `status` | String | `uploaded` / `processed` | Status file |
| `parent_id` | String | `IMG-1234...` / `-` | Ref ke foto original |

---

## 🧠 Fitur Error Handling

Aplikasi menangani skenario error berikut dengan message yang user-friendly:

| Skenario | Notifikasi |
|---|---|
| LocalStack mati / tidak terhubung | `st.warning()` dengan instruksi start Docker |
| S3 bucket tidak bisa dibuat | `st.error()` |
| DynamoDB tabel tidak aktif | Auto wait + timeout message |
| Upload gagal | Rollback (hapus S3 jika DB gagal) |
| File corrupt / format invalid | `st.error("File gambar corrupt...")` |
| Gagal resize / edit | `st.error()` dengan pesan exception |
| File tidak ditemukan di S3 | `st.error()` |
| Konfirmasi delete | Modal confirmation "Ya, Hapus Permanen" / "Batal" |

Gunakan: `st.success()` ✅, `st.error()` ❌, `st.warning()` ⚠️, `st.info()` ℹ️

---

## 🎓 Panduan Presentasi (Untuk Dosen)

### File yang Perlu Dijelaskan per Teknologi:

| Teknologi | File Penanggung Jawab | Penjelasan Singkat |
|---|---|---|
| **Streamlit** | 📄 [app.py](file:///C:/Users/Asus/Documents/trae_projects/umkm/app.py) | Seluruh UI (Dashboard, Upload, Editor, Gallery, Cloud Storage) |
| **Boto3** | 📄 [s3_service.py](file:///C:/Users/Asus/Documents/trae_projects/umkm/services/s3_service.py) & [dynamodb_service.py](file:///C:/Users/Asus/Documents/trae_projects/umkm/services/dynamodb_service.py) | Integrasi AWS SDK (S3 client + DynamoDB resource) ke LocalStack |
| **LocalStack** | 📄 [docker-compose.yml](file:///C:/Users/Asus/Documents/trae_projects/umkm/docker-compose.yml) | Konfigurasi Docker untuk S3 + DynamoDB di port 4566 |
| **Amazon S3** | 📄 [s3_service.py](file:///C:/Users/Asus/Documents/trae_projects/umkm/services/s3_service.py#L1-L150) | Class `S3Service`: upload, download, delete, list object, storage stats |
| **Amazon DynamoDB** | 📄 [dynamodb_service.py](file:///C:/Users/Asus/Documents/trae_projects/umkm/services/dynamodb_service.py#L1-L150) | Class `DynamoDBService`: create_table, put_item, get_item, scan, query |
| **Pillow / PIL** | 📄 [image_service.py](file:///C:/Users/Asus/Documents/trae_projects/umkm/services/image_service.py#L1-L150) | Class `ImageService`: Resize, Grayscale, Sepia, Invert, Watermark, Convert Format |
| **Config** | 📄 [settings.py](file:///C:/Users/Asus/Documents/trae_projects/umkm/config/settings.py) | Load `.env`, BOTO3_CONFIG, allowed formats, default watermark |
| **Utilities** | 📄 [helpers.py](file:///C:/Users/Asus/Documents/trae_projects/umkm/utils/helpers.py) | generate_image_id, format_file_size, build_s3_key, image_to_bytesio |

### Alur Demo untuk Presentasi:
1. 🐳 Jalankan `docker compose up -d` → tunggu LocalStack siap
2. 🐍 Jalankan `streamlit run app.py`
3. 🏠 Tampilkan **Dashboard** & status koneksi (semua 🟢)
4. 📤 Upload 2-3 produk (contoh: keripik.jpg, baju.png)
5. 🎨 Buka **Image Editor**:
   - Resize → ukuran lebih kecil
   - Watermark → tambah © Nama UMKM
   - Convert ke WEBP → lihat penghematan size
   - Save salah satu ke S3
6. 🖼️ Buka **Product Gallery** → filter original & processed, coba View/Download/Delete
7. ☁️ Buka **Cloud Storage** → buktikan object bertambah di S3 & DynamoDB
8. 💻 Verifikasi via CLI AWS: `aws --endpoint-url=http://localhost:4566 s3 ls s3://mini-cloud-umkm-products --recursive`

---

## ⚠️ Catatan Penting

- **Jangan** gunakan AWS Cloud asli — semua koneksi diarahkan ke `http://localhost:4566`
- **Jangan** lupa jalankan `docker compose up -d` SEBELUM `streamlit run app.py`
- Untuk **Windows**, pastikan Docker Desktop berjalan dengan WSL2 atau Hyper-V
- Jika `arial.ttf` tidak ditemukan untuk watermark, Pillow otomatis fallback ke `ImageFont.load_default()`
- Semua bucket & tabel dibuat **otomatis** oleh fungsi `initialize_services()` di app.py

---

## 📜 Lisensi

Project untuk keperluan akademis (Mata Kuliah Cloud Computing).

---

**✨ Selamat mencoba Mini Cloud Image Studio!**
