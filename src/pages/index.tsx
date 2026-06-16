import Navbar from '@/components/Navbar';

const projectStructure = String.raw`traffic-density/
|-- api/                    # Backend FastAPI
|   |-- main.py             # Titik masuk API Backend
|   |-- engine.py           # Inferensi YOLO dan kalkulasi kepadatan
|   |-- bmd45_loader.py     # Pengunduh gambar BMD-45
|   |-- session_manager.py  # Sesi analisis lalu lintas
|   \-- requirements.txt    # Dependensi Python
|-- latest_run/             # Artifak model/konfigurasi
|-- src/                    # Frontend Next.js
|   |-- components/         # Komponen UI
|   \-- pages/              # Halaman dan rute proxy API
|-- package.json            # Skrip frontend
\-- README.md`;

const backendSetup = String.raw`cd api
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000`;

const frontendSetup = `npm install
npm run dev`;

const executionPolicy = `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`;

const algorithmPillars = [
  {
    title: '1. Snapshot',
    icon: 'photo_camera',
    color: 'bg-primary-fixed text-primary',
    body: 'Sistem mengambil data kepadatan dari seluruh lajur jalan secara serentak pada awal siklus (waktu T=0). Data ini kemudian dikunci untuk diproses dalam satu putaran penuh. Perubahan arus lalu lintas baru di tengah putaran diabaikan sementara untuk mencegah lajur padat memotong antrean terus-menerus.',
  },
  {
    title: '2. Priority Queue',
    icon: 'sort',
    color: 'bg-secondary-fixed text-secondary',
    body: 'Lajur jalan yang telah dipotret dimasukkan ke dalam struktur data antrean berprioritas. Lajur dengan tingkat kepadatan kendaraan tertinggi ditempatkan di urutan pertama untuk mendapatkan giliran lampu hijau terlebih dahulu.',
  },
  {
    title: '3. Round-Robin',
    icon: 'sync',
    color: 'bg-tertiary-fixed text-tertiary',
    body: 'Meskipun diurutkan berdasarkan prioritas, sistem menjamin semua lajur jalan mendapatkan hak jalan tepat satu kali dalam satu siklus penuh sebelum sistem mengambil snapshot baru untuk iterasi berikutnya.',
  },
];

const features = [
  ['add_road', 'Konfigurasi Lajur', 'Pemilihan lajur jalan mulai dari 1 hingga 4 lajur secara dinamis.'],
  ['troubleshoot', 'Deteksi YOLO', 'Deteksi kendaraan berbasis model YOLO langsung pada gambar lalu lintas.'],
  ['calculate', 'Kalkulasi Kepadatan', 'Kalkulasi persentase kepadatan lalu lintas berdasarkan jumlah objek terdeteksi.'],
  ['timer', 'Alokasi Dinamis', 'Alokasi durasi lampu hijau yang dinamis berdasarkan tingkat kepadatan lajur.'],
  ['wifi_tethering', 'Live Polling', 'Pembaruan status sesi langsung dari backend setiap 2 detik untuk visualisasi real-time.'],
];

const techStack = [
  ['web', 'Frontend', 'Next.js 15, React 19, TypeScript, Tailwind CSS'],
  ['dns', 'Backend', 'FastAPI, Uvicorn, Ultralytics YOLOv8, OpenCV'],
  ['database', 'Sumber Dataset', 'iisc-aim/BMD-45 dari Hugging Face'],
];

export default function HomePage() {
  return (
    <div className="bg-surface text-on-surface font-body-md min-h-screen antialiased">
      <Navbar activePage="home" />

      <main className="px-container-padding py-20 max-w-7xl mx-auto space-y-32">
        <section className="relative pt-10 pb-8 flex flex-col items-center text-center">
          <div className="glow-effect top-0 left-1/2 -translate-x-1/2 opacity-50" />
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-secondary-fixed text-on-secondary-fixed font-label-md text-label-md mb-6">
            <span className="material-symbols-outlined text-[14px]">science</span>
            Precision Analytics System
          </div>
          <h1 className="font-headline-lg text-headline-lg-mobile md:text-headline-lg text-on-surface mb-6 max-w-3xl">
            How Traffic Light AI Works
          </h1>
          <p className="font-body-lg text-body-lg text-on-surface-variant max-w-2xl mb-10">
            Aplikasi web untuk mensimulasikan lampu merah jalan raya menggunakan kepadatan jalan dan algoritma Snapshot-based Priority Scheduling untuk menyesuaikan urutan prioritas fase lampu lalu lintas secara adil dan efisien.
          </p>
          <div className="flex flex-col sm:flex-row gap-4">
            <a className="bg-primary text-on-primary px-6 py-3 rounded-lg font-label-lg text-label-lg hover:bg-surface-tint transition-colors flex items-center justify-center gap-2 shadow-sm hover:shadow-md" href="#setup">
              <span className="material-symbols-outlined">rocket_launch</span>
              View Setup Guide
            </a>
            <a className="border border-outline text-on-surface px-6 py-3 rounded-lg font-label-lg text-label-lg hover:bg-surface-container transition-colors flex items-center justify-center gap-2" href="https://github.com/hans3I/traffic-density" target="_blank" rel="noreferrer">
              <span className="material-symbols-outlined">terminal</span>
              GitHub Repository
            </a>
          </div>
        </section>

        <section className="scroll-mt-24" id="algorithm">
          <div className="mb-12">
            <h2 className="font-headline-md text-headline-md text-on-surface mb-4">Algoritma Penjadwalan: Snapshot-based Priority Scheduling</h2>
            <p className="font-body-md text-body-md text-on-surface-variant max-w-3xl">
              Aplikasi ini mengimplementasikan pendekatan gabungan tiga konsep dasar algoritma untuk menciptakan sistem pengaturan lalu lintas yang optimal dan etis.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
            {algorithmPillars.map((pillar) => (
              <div key={pillar.title} className="bg-surface-container-lowest border border-surface-variant rounded-xl p-6 hover:shadow-[0_4px_12px_rgba(45,125,142,0.05)] transition-shadow">
                <div className={`w-12 h-12 rounded-lg flex items-center justify-center mb-6 ${pillar.color}`}>
                  <span className="material-symbols-outlined icon-fill">{pillar.icon}</span>
                </div>
                <h3 className="font-headline-sm text-headline-sm text-on-surface mb-3">{pillar.title}</h3>
                <p className="font-body-md text-body-md text-on-surface-variant">{pillar.body}</p>
              </div>
            ))}
          </div>

          <div className="bg-primary-fixed border border-inverse-primary rounded-xl p-8 flex flex-col md:flex-row gap-8 items-start">
            <div className="w-16 h-16 shrink-0 rounded-full bg-surface-container-lowest flex items-center justify-center shadow-sm">
              <span className="material-symbols-outlined icon-fill text-primary text-3xl">local_hospital</span>
            </div>
            <div>
              <h4 className="font-headline-sm text-headline-sm text-on-primary-fixed-variant mb-2">Pro Tip: Analogi Sistem (Ruang Gawat Darurat)</h4>
              <p className="font-body-md text-body-md text-on-primary-fixed-variant leading-relaxed">
                Pendekatan ini mirip dengan manajemen pasien di Ruang Gawat Darurat (UGD). Jika menggunakan giliran murni (Pure Round-Robin), pasien kritis bisa tidak tertolong karena mengantre di belakang pasien batuk-pilek. Jika menggunakan prioritas murni (Pure Priority), pasien batuk-pilek tidak akan pernah dilayani karena selalu ada pasien kecelakaan baru yang masuk. Dengan algoritma ini, dokter mendata seluruh pasien (Snapshot), mengurutkan dari yang kritis (Priority), lalu memeriksa semua satu per satu (Round-Robin).
              </p>
            </div>
          </div>
        </section>

        <section className="scroll-mt-24" id="features">
          <h2 className="font-headline-md text-headline-md text-on-surface mb-8">Fitur Utama</h2>
          <div className="bento-grid">
            {features.map(([icon, title, body], index) => (
              <div key={title} className={`bg-surface-container-lowest border border-surface-variant rounded-xl p-6 flex gap-4 ${index === 4 ? 'md:col-span-2' : ''}`}>
                <span className="material-symbols-outlined text-primary text-2xl mt-1">{icon}</span>
                <div>
                  <h4 className="font-label-lg text-label-lg text-on-surface mb-2">{title}</h4>
                  <p className="font-body-md text-body-md text-on-surface-variant">{body}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="scroll-mt-24" id="tech-stack">
          <h2 className="font-headline-md text-headline-md text-on-surface mb-8">Technical Architecture</h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
            <div className="space-y-4">
              <h3 className="font-headline-sm text-headline-sm text-on-surface">Teknologi yang Digunakan</h3>
              {techStack.map(([icon, label, body]) => (
                <div key={label} className="bg-surface-container-lowest border border-surface-variant rounded-xl p-5 flex items-center gap-4">
                  <div className="w-10 h-10 rounded bg-surface-container flex items-center justify-center">
                    <span className="material-symbols-outlined text-on-surface-variant">{icon}</span>
                  </div>
                  <div>
                    <div className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider mb-1">{label}</div>
                    <div className="font-body-md text-body-md text-on-surface font-medium">{body}</div>
                  </div>
                </div>
              ))}
            </div>

            <div>
              <h3 className="font-headline-sm text-headline-sm text-on-surface mb-4">Struktur Proyek</h3>
              <pre className="code-block text-sm">{projectStructure}</pre>
            </div>
          </div>

          <div className="bg-surface-container-low border border-surface-variant rounded-xl p-6">
            <h3 className="font-headline-sm text-headline-sm text-on-surface mb-4 flex items-center gap-2">
              <span className="material-symbols-outlined text-secondary">memory</span>
              Persyaratan Sistem
            </h3>
            <ul className="list-disc list-inside space-y-2 font-body-md text-body-md text-on-surface-variant ml-2">
              <li>Node.js 18 atau versi yang lebih baru</li>
              <li>Python 3.10 atau versi yang lebih baru</li>
              <li>Koneksi internet aktif untuk eksekusi backend pertama kali (mengunduh metadata/gambar dari Hugging Face)</li>
              <li>File model YOLO diletakkan di <code className="bg-surface-container-highest px-1 rounded">latest_run/outputs/best.pt</code>, atau atur env <code className="bg-surface-container-highest px-1 rounded">TRAFFICAI_MODEL_PATH</code></li>
            </ul>
          </div>
        </section>

        <section className="scroll-mt-24" id="setup">
          <h2 className="font-headline-md text-headline-md text-on-surface mb-8">Setup Guide</h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div className="bg-surface-container-lowest border border-surface-variant rounded-xl overflow-hidden">
              <div className="bg-surface-container-low px-6 py-4 border-b border-surface-variant flex items-center justify-between">
                <h3 className="font-headline-sm text-headline-sm text-on-surface flex items-center gap-2">
                  <span className="material-symbols-outlined">terminal</span>
                  Pengaturan Backend
                </h3>
              </div>
              <div className="p-6 space-y-4">
                <p className="font-body-md text-body-md text-on-surface-variant">Buka terminal di direktori utama proyek, jalankan:</p>
                <pre className="code-block text-sm">{backendSetup}</pre>
                <div className="font-body-md text-body-md text-on-surface-variant">
                  <p>Backend berjalan di: <code className="text-primary">http://127.0.0.1:8000</code></p>
                  <p>Health check: <code className="text-primary">http://127.0.0.1:8000/api/v1/health</code></p>
                </div>
                <div className="mt-4 pt-4 border-t border-surface-variant">
                  <p className="font-label-md text-label-md text-on-surface-variant mb-2">Jika PowerShell memblokir aktivasi venv:</p>
                  <pre className="code-block text-sm">{executionPolicy}</pre>
                </div>
              </div>
            </div>

            <div className="bg-surface-container-lowest border border-surface-variant rounded-xl overflow-hidden">
              <div className="bg-surface-container-low px-6 py-4 border-b border-surface-variant flex items-center justify-between">
                <h3 className="font-headline-sm text-headline-sm text-on-surface flex items-center gap-2">
                  <span className="material-symbols-outlined">web_asset</span>
                  Pengaturan Frontend
                </h3>
              </div>
              <div className="p-6 space-y-4">
                <p className="font-body-md text-body-md text-on-surface-variant">Buka terminal kedua di direktori utama proyek, jalankan:</p>
                <pre className="code-block text-sm">{frontendSetup}</pre>
                <div className="bg-primary-fixed/20 p-4 rounded-lg mt-4 border border-primary-fixed-dim">
                  <p className="font-body-md text-body-md text-on-surface-variant flex gap-3">
                    <span className="material-symbols-outlined text-primary mt-0.5">info</span>
                    <span>Frontend akan berjalan pada <code className="font-medium text-primary">http://localhost:3000</code>. Pastikan server backend tetap berjalan di port 8000. Rute API Next.js bertindak sebagai proxy.</span>
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

      </main>
    </div>
  );
}
