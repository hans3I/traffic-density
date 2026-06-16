# Traffic Light AI

Traffic Light AI merupakan aplikasi web untuk mensimulasikan lampu merah jalan raya menggunakan kepadatan jalan dan algoritma Snapshot-based Priority Scheduling untuk menyesuaikan urutan prioritas fase lampu lalu lintas secara adil dan efisien.

## Algoritma Penjadwalan: Snapshot-based Priority Scheduling

Aplikasi ini mengimplementasikan pendekatan gabungan tiga konsep dasar algoritma untuk menciptakan sistem pengaturan lalu lintas yang optimal dan etis:

1. **Snapshot**
Sistem mengambil data kepadatan dari seluruh lajur jalan secara serentak pada awal siklus (waktu T=0). Data ini kemudian dikunci untuk diproses dalam satu putaran penuh. Perubahan arus lalu lintas baru yang terjadi di tengah putaran akan diabaikan sementara hingga siklus berjalan selesai. Hal ini berfungsi sebagai pengunci keadaan untuk mencegah lajur yang sangat padat memotong antrean secara terus-menerus.

2. **Priority Queue**
Lajur jalan yang telah dipotret akan dimasukkan ke dalam struktur data antrean berprioritas. Lajur dengan tingkat kepadatan kendaraan tertinggi akan ditempatkan di urutan pertama untuk mendapatkan giliran lampu hijau terlebih dahulu.

3. **Round-Robin**
Meskipun diurutkan berdasarkan prioritas kepadatan, sistem menjamin bahwa semua lajur jalan (dari yang paling padat hingga yang paling sepi) akan mendapatkan hak jalan tepat satu kali dalam satu siklus penuh sebelum sistem melakukan pengambilan snapshot baru untuk iterasi berikutnya.

### Analogi Sistem (Ruang Gawat Darurat)
Pendekatan ini mirip dengan manajemen pasien di Ruang Gawat Darurat (UGD). Jika menggunakan giliran murni (Pure Round-Robin), pasien kritis bisa tidak tertolong karena mengantre di belakang pasien batuk-pilek. Jika menggunakan prioritas murni (Pure Priority), pasien batuk-pilek tidak akan pernah dilayani karena selalu ada pasien kecelakaan baru yang masuk. Dengan Snapshot-based Priority Scheduling, dokter mendata seluruh pasien yang ada di ruangan pada saat itu (Snapshot), mengurutkannya dari yang paling kritis (Priority), lalu memeriksa mereka semua satu per satu hingga selesai (Round-Robin). Pasien kritis diselamatkan terlebih dahulu, dan pasien bergejala ringan tetap mendapatkan kepastian pelayanan.

## Fitur Utama

- Pemilihan lajur jalan mulai dari 1 hingga 4 lajur.
- Deteksi kendaraan berbasis model YOLO langsung pada gambar lalu lintas.
- Kalkulasi persentase kepadatan lalu lintas berdasarkan jumlah objek yang terdeteksi.
- Alokasi durasi lampu hijau yang dinamis berdasarkan tingkat kepadatan lajur dan prioritas antrean.
- Pembaruan status sesi langsung (*live polling*) dari backend setiap 2 detik.

## Teknologi yang Digunakan

- **Frontend:** Next.js 15, React 19, TypeScript, Tailwind CSS
- **Backend:** FastAPI, Uvicorn, Ultralytics YOLOv8, OpenCV
- **Sumber Dataset:** `iisc-aim/BMD-45` dari Hugging Face

## Struktur Proyek

```text
traffic-density/
|-- api/                    # Backend FastAPI
|   |-- main.py             # Titik masuk API Backend
|   |-- engine.py           # Inferensi YOLO dan kalkulasi kepadatan
|   |-- bmd45_loader.py     # Pengunduh gambar BMD-45
|   |-- session_manager.py  # Sesi analisis lalu lintas dan pengatur waktu
|   `-- requirements.txt    # Dependensi Python
|-- latest_run/             # Artifak model/konfigurasi yang digunakan backend
|-- src/                    # Frontend Next.js
|   |-- components/         # Komponen UI
|   `-- pages/              # Halaman dan rute proxy API
|-- package.json            # Skrip frontend dan dependensi
`-- README.md

```

## Persyaratan Sistem

* Node.js 18 atau versi yang lebih baru
* Python 3.10 atau versi yang lebih baru
* Koneksi internet aktif untuk eksekusi backend pertama kali (karena metadata/gambar BMD-45 diunduh otomatis dari Hugging Face)
* File model YOLO diletakkan di `latest_run/outputs/best.pt`, atau dengan mengatur variabel lingkungan `TRAFFICAI_MODEL_PATH` ke jalur model yang valid

## Pengaturan Backend

Buka terminal di direktori utama proyek, kemudian jalankan perintah berikut:

```powershell
cd api
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000

```

Backend akan berjalan pada alamat: `http://127.0.0.1:8000`

Pemeriksaan status server (Health check): `http://127.0.0.1:8000/api/v1/health`

Jika PowerShell memblokir aktivasi environment virtual, jalankan perintah ini sekali di terminal yang sama:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

```

Kemudian aktifkan kembali environment tersebut:

```powershell
.\.venv\Scripts\Activate.ps1

```

## Pengaturan Frontend

Buka terminal kedua di direktori utama proyek, lalu jalankan:

```powershell
npm install
npm run dev

```

Frontend akan berjalan pada alamat: `http://localhost:3000`

Pastikan server backend tetap berjalan di port `8000` selama menggunakan frontend. Rute API Next.js pada `src/pages/api/traffic.ts` bertindak sebagai proxy untuk meneruskan permintaan dari frontend ke `http://127.0.0.1:8000`.

## Endpoint API

### Memulai Analisis

```http
POST /api/v1/start

```

Request body:

```json
{
  "lanes": 4,
  "max_green_time": 60
}

```

### Mendapatkan Status Sesi

```http
GET /api/v1/state/{session_id}

```

### Mengonfigurasi Sesi

```http
POST /api/v1/configure

```

Request body:

```json
{
  "session_id": "example-id",
  "max_green_time": 60
}

```

### Pengecekan Kesehatan Server

```http
GET /api/v1/health

```

## Jalur Model (Model Path)

Secara bawaan, backend mencari model YOLO dengan urutan prioritas berikut:

1. Variabel lingkungan `TRAFFICAI_MODEL_PATH`
2. Jalur yang dikonfigurasi dalam `latest_run/config/default.yaml`
3. File pada `latest_run/outputs/best.pt`
4. File `best.pt` pada direktori utama proyek

Untuk menetapkan jalur model kustom di PowerShell, gunakan perintah:

```powershell
$env:TRAFFICAI_MODEL_PATH = "C:\path\to\best.pt"
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000

```

## Masalah yang mungkin ditemui

* `Backend connection failed`: Pastikan server FastAPI sudah berjalan dengan benar di alamat `127.0.0.1:8000`.
* `No YOLO model found`: Pastikan file model telah diletakkan di `latest_run/outputs/best.pt` atau variabel lingkungan `TRAFFICAI_MODEL_PATH` telah diatur dengan benar.
* Analisis awal lambat: Backend kemungkinan sedang mengunduh anotasi/gambar BMD-45 dari Hugging Face atau sedang memuat model YOLO ke dalam memori untuk pertama kali.
* Kesalahan unduhan Hugging Face: Periksa stabilitas koneksi internet Anda lalu ulangi proses.

## Skrip yang Tersedia

Perintah untuk Frontend:

```powershell
npm run dev
npm run build
npm run start
npm run lint

```

Perintah untuk Backend:

```powershell
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000

```
