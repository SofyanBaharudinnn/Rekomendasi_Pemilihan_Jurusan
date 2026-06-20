# 🎓 JurusanKu ID — Platform Rekomendasi Jurusan Berbasis Machine Learning

JurusanKu ID adalah platform web interaktif dan premium yang dirancang untuk membantu siswa SMA/SMK/Sederajat menentukan jurusan kuliah yang paling sesuai dengan potensi akademik dan minat mereka. Menggunakan algoritma Machine Learning **Decision Tree Classifier**, JurusanKu ID menganalisis nilai mata pelajaran serta kecenderungan minat siswa untuk memberikan rekomendasi top 3 jurusan kuliah secara akurat.

---

## 🌟 Fitur Utama

### 1. 🤖 Rekomendasi Jurusan Berbasis ML (Decision Tree)

* Menganalisis 4 nilai mata pelajaran utama: **Matematika, Bahasa, IPA, dan IPS**.
* Menganalisis 4 metrik minat siswa: **Teknologi, Seni, Bisnis, dan Kesehatan**.
* Menghasilkan **Top 3 Jurusan Rekomendasi** dengan persentase kecocokan yang dinamis dan terkalibrasi secara akurat dengan kelas hasil prediksi utama.
* Dilengkapi dengan fitur **Cetak Hasil** (print-friendly) untuk memudahkan siswa mengunduh atau mencetak laporan rekomendasi mereka.

### 2. 🎮 Sistem Gamifikasi & Poin (Engagement)

* **Sistem Poin**: Siswa mendapatkan poin setiap kali menyelesaikan profil, melakukan tes rekomendasi, membaca artikel, atau menjelajahi detail jurusan.
* **Lencana Pencapaian (Badges)**: Penghargaan lencana khusus seperti *Pemula*, *Rajin Tes*, *Expert*, *Profil Lengkap*, *Poin 100*, *Pembaca*, dan *Penjelajah* untuk mendorong interaktivitas siswa.
* **Riwayat Poin**: Log transparan mengenai cara siswa memperoleh poin mereka.

### 3. 💬 Forum Diskusi Interaktif

* Komunitas belajar tempat siswa dapat berdiskusi, bertanya, dan berkomentar mengenai persiapan UTBK, kehidupan kampus, karir, dan topik umum lainnya.
* Pengkategorian forum yang rapi untuk mempermudah pencarian informasi.

### 4. 📈 Panel Admin Komprehensif (Dashboard Admin)

* **Analisis Data**: Grafik visual sebaran rekomendasi jurusan siswa, rata-rata nilai, dan aktivitas terbaru.
* **CRUD Manajemen Konten**: Kelola data Jurusan, Artikel, FAQ, dan Testimoni secara langsung tanpa melalui database.
* **Manajemen Model ML**: Pantau versi model aktif, ukuran dataset, algoritma, serta akurasi pelatihan.
* **Log Keamanan**: Monitor riwayat aktivitas pengguna untuk mendeteksi tindakan mencurigakan.

### 5. 🛡️ Keamanan & Logging Aktivitas

* Proteksi halaman dengan dekorator akses peran (admin vs. siswa).
* Log keamanan otomatis untuk melacak aktivitas penting seperti: *Login Gagal*, *Akses Ditolak*, *Captcha Gagal*, *Register Gagal*, *Session Timeout*, dan *Login Sukses*.
* Captcha dinamis pada halaman login dan register untuk mencegah serangan bot/brute-force.

### 6. 🎨 UI/UX Premium & Responsif

* Desain modern dengan nuansa gelap (*dark mode*) yang elegan, efek *glassmorphism*, dan transisi halus.
* **Animasi Interaktif**: Grafis latar belakang jaringan koneksi saraf (*neural network*) dinamis yang menggunakan **Three.js**.
* **Optimasi Performa**: Render grafis 3D telah dioptimalkan dengan alokasi buffer geometri dinamis sehingga halaman beranda terasa sangat ringan dan bebas dari stuttering/lag saat dimuat ulang.
* **Responsif Penuh**: Tata letak yang dioptimalkan dengan vanilla CSS agar tampil sempurna di perangkat mobile, tablet, maupun desktop.

---

## 🛠️ Teknologi yang Digunakan

* **Backend**: Django 6.0.6 (Python)
* **Frontend**: Vanilla HTML5, CSS3, JavaScript (ES6+), Three.js (WebGL Animation)
* **Machine Learning**: scikit-learn 1.9.0, pandas 3.0.3, numpy 2.4.6, joblib 1.5.3
* **Database**: SQLite (Default Django)
* **Middleware Performa**: WhiteNoise (untuk penyajian aset statis yang cepat)

---

## 🚀 Panduan Instalasi & Menjalankan Lokal

Ikuti langkah-langkah di bawah ini untuk menjalankan proyek JurusanKu ID di komputer lokal Anda:

### Prasyarat

Pastikan Anda sudah menginstal **Python (versi 3.10 atau lebih baru)** dan **Git** di komputer Anda.

### 1. Persiapan Environment

1. Ekstrak proyek atau klon repositori ini.
2. Buka terminal/command prompt di direktori proyek tersebut.
3. Buat virtual environment Python baru:

   ```bash
   python -m venv venv
   ```

4. Aktifkan virtual environment:
   * **Windows (Command Prompt)**:

     ```cmd
     venv\Scripts\activate
     ```

   * **Windows (PowerShell)**:

     ```powershell
     .\venv\Scripts\Activate.ps1
     ```

   * **Linux / macOS**:

     ```bash
     source venv/bin/activate
     ```

### 2. Instalasi Dependensi

Setelah virtual environment aktif, instal semua pustaka yang diperlukan dengan menjalankan perintah:

```bash
pip install -r requirements.txt
```

### 3. Migrasi Database

Jalankan migrasi untuk membuat struktur tabel database SQLite lokal:

```bash
python manage.py migrate
```

### 4. Menjalankan Server Pengembangan

Jalankan server lokal Django:

```bash
python manage.py runserver
```

Buka browser Anda dan akses alamat: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

---

## 🤖 Panduan Pelatihan Ulang Model ML (Retraining Model)

Data model prediksi tersimpan di dalam folder `ml_model/`. Jika Anda ingin melatih ulang model Decision Tree dengan dataset terbaru:

1. Pastikan virtual environment Anda aktif.
2. Edit atau tambahkan data pada berkas `ml_model/dataset.csv` jika diperlukan.
3. Jalankan script pelatihan:

   ```bash
   python ml_model/train.py
   ```

4. Script akan melatih model baru, menampilkan tingkat akurasi model, dan menyimpan hasilnya dalam berkas `ml_model/model.pkl` yang secara otomatis akan digunakan oleh sistem rekomendasi Django.

---

## 📂 Struktur Direktori Proyek

```text
jurusan-rekomendasi/
│
├── config/                  # Pengaturan utama proyek Django (settings, urls, wsgi)
├── rekomendasi/             # Aplikasi Django utama (views, models, migrations, security)
├── ml_model/                # Model Machine Learning (dataset.csv, train.py, model.pkl)
├── templates/               # Berkas HTML template (index, dashboard, forum, dll.)
├── static/                  # Berkas statis (CSS, JS kustom, Gambar)
├── media/                   # Berkas unggahan pengguna (seperti avatar profil)
├── manage.py                # Utilitas CLI Django
├── requirements.txt         # Daftar pustaka/dependensi Python
└── README.md                # Dokumentasi proyek (berkas ini)
```

---

## 📄 Lisensi

Proyek ini dikembangkan untuk tujuan edukasi dan membantu mempermudah siswa dalam memilih masa depan akademiknya secara cerdas dan terarah.
