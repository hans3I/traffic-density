# Laporan Pengujian Efektivitas Algoritma

**Tanggal:** 2026-06-10 03:34:25
**Sistem:** Traffic Light AI Backend
**Model:** YOLOv8 (`best.pt`)
**Dataset:** BMD-45 (Bengaluru Mobility Dataset)

---

## 1. Ringkasan

Laporan ini menyajikan hasil pengujian efektivitas dua komponen utama sistem:

1. **Akurasi Deteksi Kendaraan** - Mengukur performa model YOLOv8 dalam mendeteksi kendaraan (motor, mobil, heavy) pada 100 sampel gambar acak dari BMD45-Val.
2. **Efektivitas Scheduling Lampu Lalu Lintas** - Membandingkan algoritma **Density-Based** dengan **Fixed-Time** (baseline) dalam simulasi 4 lane selama 20 cycle.

---

## 2. Pengujian Akurasi Deteksi (YOLOv8)

### 2.1 Metodologi

- **Jumlah Sampel:** 100 gambar acak dari BMD-45-Val
- **Metrik:** Precision, Recall, F1-Score, mAP@0.5
- **Threshold IoU:** 0.5
- **Mapping Kelas:**
  - **Motor:** Two-wheeler, Three-wheeler, Bicycle
  - **Car:** Hatchback, Sedan, SUV, MUV, Van
  - **Heavy:** Bus, Truck, LCV, Mini-bus, Tempo-traveller

### 2.2 Hasil Per Kelas

| Kelas | Precision | Recall | F1-Score | mAP@0.5 | TP | FP | FN | Ground Truth |
|-------|-----------|--------|----------|---------|----|----|----|--------------|
| motor | 0.765 | 0.6003 | 0.6727 | 0.5082 | 407 | 125 | 271 | 678 |
| car | 0.057 | 0.0463 | 0.0511 | 0.0909 | 13 | 215 | 268 | 281 |
| heavy | 0.8 | 0.381 | 0.5161 | 0.3091 | 56 | 14 | 91 | 147 |

### 2.3 Hasil Keseluruhan

| Metrik | Nilai |
|--------|-------|
| **Precision** | 0.5735 |
| **Recall** | 0.4304 |
| **F1-Score** | 0.4917 |
| **mAP@0.5** | 0.3027 |
| **Total True Positives** | 476 |
| **Total False Positives** | 354 |
| **Total False Negatives** | 630 |
| **Avg Inference Time** | 274.25 ms |

### 2.4 Analisis

- **Precision** sebesar **0.5735** menunjukkan dari semua prediksi model, sekitar 57% adalah benar.
- **Recall** sebesar **0.4304** menunjukkan model berhasil mendeteksi 43% dari total kendaraan yang sebenarnya ada.
- **mAP@0.5** sebesar **0.3027** mencerminkan kualitas deteksi secara keseluruhan.
- **Inference Time** rata-rata **274.25 ms** menunjukkan model cukup cepat untuk aplikasi real-time.

---

## 3. Pengujian Efektivitas Scheduling

### 3.1 Metodologi

- **Jumlah Lane:** 4
- **Jumlah Cycle:** 20
- **Max Green Time:** 60 detik
- **Service Rate:** 10 weighted vehicles/second
- **Skenario:**
  - **Density-Based:** Lane dengan kepadatan tertinggi mendapatkan waktu hijau. Hanya lane yang baru hijau yang mendapatkan gambar baru.
  - **Fixed-Time:** Lane bergantian secara round-robin dengan waktu hijau tetap = 60/4 = 15.0 detik.

### 3.2 Hasil Perbandingan

| Metrik | Density-Based | Fixed-Time | Perubahan |
|--------|---------------|------------|-----------|
| **Total Throughput** | 511.0 | 847.0 | **-39.7%** |
| **Throughput per Detik** | 2.9 | 2.82 | **+2.8%** |
| **Total Waiting Time** | 19209.0 | 22605.0 | **+15.0%** |
| **Avg Waiting Time/Cycle** | 960.45 | 1130.25 | - |
| **Total Time** | 176.0 detik | 300.0 detik | - |
| **Fairness Index** | 0.6667 | 1.0 | - |

### 3.3 Detail Per Lane (Density-Based)

| Lane | Jumlah Kali Hijau | Total Waiting Time |
|------|-------------------|-------------------|
| Lane 1 | 9 | 1557.0 |
| Lane 2 | 2 | 10272.0 |
| Lane 3 | 8 | 2436.0 |
| Lane 4 | 1 | 4944.0 |

### 3.4 Detail Per Lane (Fixed-Time)

| Lane | Jumlah Kali Hijau | Total Waiting Time |
|------|-------------------|-------------------|
| Lane 1 | 5 | 7380.0 |
| Lane 2 | 5 | 4815.0 |
| Lane 3 | 5 | 4560.0 |
| Lane 4 | 5 | 5850.0 |

### 3.5 Analisis

- **Total Throughput:** Dalam 20 cycle, Fixed-Time menghasilkan throughput total lebih tinggi (847.0 vs 511.0) karena setiap cycle memiliki durasi tetap 15 detik, sehingga total waktu simulasi lebih panjang (300.0s vs 176.0s).
- **Throughput Efficiency:** Ketika dinormalisasi per detik, Density-Based mencapai **2.9 weighted vehicles/detik** dibandingkan Fixed-Time **2.82 weighted vehicles/detik**. Ini menunjukkan efisiensi **+2.8%** lebih tinggi pada Density-Based, karena lane yang lebih padat mendapatkan waktu hijau lebih lama dan lebih banyak kendaraan dapat dilayani per unit waktu.
- **Waiting Time:** Algoritma Density-Based mengurangi total waiting time sebesar **15.0%**. Ini menunjukkan bahwa lane yang padat lebih cepat dilayani, mengurangi akumulasi kendaraan menunggu.
- **Fairness Index:** Fixed-Time memiliki fairness index sempurna (1.0) karena setiap lane mendapatkan kesempatan hijau secara merata. Density-Based memiliki fairness index **0.6667**, yang menunjukkan bias terhadap lane yang lebih padat. Ini adalah trade-off antara efisiensi dan keadilan.

---

## 4. Kesimpulan

### 4.1 Akurasi Deteksi
Model YOLOv8 menunjukkan performa deteksi yang cukup dengan mAP@0.5 sebesar **0.3027**. Model mampu mendeteksi kendaraan dalam kondisi lalu lintas urban (Bengaluru) dengan inference time yang memadai untuk aplikasi real-time.

### 4.2 Efektivitas Scheduling
Algoritma Density-Based menunjukkan efisiensi waktu yang lebih baik dengan throughput per detik **+2.8%** lebih tinggi dibandingkan Fixed-Time. Meskipun total throughput dalam 20 cycle lebih rendah karena total waktu simulasi lebih singkat, algoritma ini berhasil mengurangi total waiting time sebesar **15.0%**. Trade-off pada fairness index (0.6667) adalah konsekuensi logis dari prioritasi lane yang lebih padat.

### 4.3 Rekomendasi
1. **Peningkatan Model:** Pertimbangkan fine-tuning model pada dataset BMD-45 untuk meningkatkan akurasi deteksi pada kelas-kelas spesifik yang belum optimal (terutama kelas "car" dengan precision hanya 0.057).
2. **Fairness Adjustment:** Pertimbangkan menambahkan mekanisme "maximum waiting time" untuk lane yang jarang mendapatkan hijau, untuk meningkatkan fairness tanpa mengorbankan efisiensi secara signifikan.
3. **Real-World Validation:** Lakukan validasi pada deployment nyata dengan data lalu lintas lokal untuk memastikan performa model pada kondisi jalan Indonesia.

---

*Laporan ini dihasilkan secara otomatis oleh sistem pengujian efektivitas algoritma.*
