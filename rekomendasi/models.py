# pyrefly: ignore [missing-import]
from django.db import models
# pyrefly: ignore [missing-import]
from django.contrib.auth.models import User
# pyrefly: ignore [missing-import]
from django.db.models.signals import post_save
# pyrefly: ignore [missing-import]
from django.dispatch import receiver


# ─── PROFIL SISWA ────────────────────────────────────────────────────────────
class ProfilSiswa(models.Model):
    """Ekstensi profil untuk setiap user siswa."""
    user        = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profil')
    sekolah     = models.CharField(max_length=200, blank=True)
    kelas       = models.CharField(max_length=20, blank=True)
    kota        = models.CharField(max_length=100, blank=True)
    bio         = models.TextField(max_length=300, blank=True)
    avatar      = models.ImageField(upload_to='avatars/', null=True, blank=True)
    poin        = models.IntegerField(default=0)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Profil Siswa'
        verbose_name_plural = 'Profil Siswa'

    def __str__(self):
        return f"Profil — {self.user.username}"

    def kelengkapan_persen(self):
        """Hitung persentase kelengkapan profil (0-100)."""
        fields = [
            self.user.get_full_name(),
            self.user.email,
            self.sekolah,
            self.kelas,
            self.kota,
            self.bio,
            self.avatar.name if self.avatar else None,
        ]
        terisi = sum(1 for f in fields if f)
        return round(terisi / len(fields) * 100)

    def tambah_poin(self, jumlah, alasan=''):
        self.poin += jumlah
        self.save(update_fields=['poin'])
        RiwayatPoin.objects.create(user=self.user, jumlah=jumlah, alasan=alasan)


@receiver(post_save, sender=User)
def buat_profil_otomatis(sender, instance, created, **kwargs):
    """Otomatis buat ProfilSiswa ketika User baru dibuat."""
    if created:
        ProfilSiswa.objects.get_or_create(user=instance)


# ─── BADGE / PENCAPAIAN ──────────────────────────────────────────────────────
class UserBadge(models.Model):
    """Badge yang diraih user."""
    BADGE_CHOICES = [
        ('pemula',      '🧪 Pemula'),
        ('rajin',       '🔁 Rajin Tes'),
        ('expert',      '🏆 Expert'),
        ('profil_lengkap', '📋 Profil Lengkap'),
        ('poin_100',    '⭐ Poin 100'),
        ('pembaca',     '📰 Pembaca'),
        ('explorer',    '🔍 Penjelajah'),
    ]
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='badges')
    badge      = models.CharField(max_length=30, choices=BADGE_CHOICES)
    diraih_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'badge')
        ordering = ['-diraih_at']
        verbose_name = 'Badge'
        verbose_name_plural = 'Badges'

    def __str__(self):
        return f"{self.user.username} — {self.badge}"


# ─── RIWAYAT POIN ────────────────────────────────────────────────────────────
class RiwayatPoin(models.Model):
    """Log setiap perubahan poin user."""
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='riwayat_poin')
    jumlah     = models.IntegerField()
    alasan     = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} +{self.jumlah} ({self.alasan})"


# ─── DETAIL JURUSAN ──────────────────────────────────────────────────────────
class JurusanDetail(models.Model):
    """Informasi lengkap tiap jurusan untuk halaman detail."""
    nama            = models.CharField(max_length=100, unique=True)
    mata_kuliah     = models.JSONField(default=list)   # list string
    universitas     = models.JSONField(default=list)   # list {'nama', 'kota', 'akreditasi'}
    biaya_min       = models.IntegerField(default=0)   # per semester (Rp)
    biaya_max       = models.IntegerField(default=0)
    passing_grade   = models.FloatField(default=0)     # passing grade UTBK (0-1000)
    lama_studi      = models.CharField(max_length=20, default='4 Tahun')
    gelar           = models.CharField(max_length=50, blank=True)
    deskripsi_panjang = models.TextField(blank=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Detail Jurusan'
        verbose_name_plural = 'Detail Jurusan'

    def __str__(self):
        return self.nama


# ─── HASIL REKOMENDASI ───────────────────────────────────────────────────────
class HasilRekomendasi(models.Model):
    """Rekaman setiap tes rekomendasi yang dilakukan user."""
    user       = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    jurusan    = models.CharField(max_length=100)
    top3_data  = models.JSONField(default=list)    # simpan top3 lengkap
    nilai_mat  = models.IntegerField()
    nilai_bhs  = models.IntegerField()
    nilai_ipa  = models.IntegerField()
    nilai_ips  = models.IntegerField()
    minat_tek  = models.IntegerField()
    minat_sen  = models.IntegerField()
    minat_bis  = models.IntegerField()
    minat_kes  = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Hasil Rekomendasi'
        verbose_name_plural = 'Hasil Rekomendasi'

    def __str__(self):
        u = self.user.username if self.user else 'anonim'
        return f"{u} → {self.jurusan} ({self.created_at.strftime('%d/%m/%Y')})"


# ─── JURUSAN INFO ────────────────────────────────────────────────────────────
class JurusanInfo(models.Model):
    """Data jurusan yang bisa di-CRUD dari panel admin."""
    nama      = models.CharField(max_length=100, unique=True)
    icon      = models.CharField(max_length=10, default='🎓')
    deskripsi = models.TextField()
    prospek   = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nama']
        verbose_name = 'Jurusan'
        verbose_name_plural = 'Daftar Jurusan'

    def __str__(self):
        return self.nama


# ─── ARTIKEL ─────────────────────────────────────────────────────────────────
class Artikel(models.Model):
    judul        = models.CharField(max_length=200)
    konten       = models.TextField()
    kategori     = models.CharField(max_length=50, default='Tips')
    is_published = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Artikel'
        verbose_name_plural = 'Artikel'

    def __str__(self):
        return self.judul


# ─── FAQ ─────────────────────────────────────────────────────────────────────
class FAQ(models.Model):
    pertanyaan = models.CharField(max_length=300)
    jawaban    = models.TextField()
    urutan     = models.PositiveIntegerField(default=0)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['urutan', 'id']
        verbose_name = 'FAQ'
        verbose_name_plural = 'FAQ'

    def __str__(self):
        return self.pertanyaan[:60]


# ─── MODEL VERSION ────────────────────────────────────────────────────────────
class ModelVersion(models.Model):
    STATUS_CHOICES = [
        ('active', 'Aktif'), ('archived', 'Diarsipkan'),
        ('training', 'Sedang Training'), ('failed', 'Gagal'),
    ]
    versi        = models.CharField(max_length=20)
    akurasi      = models.FloatField(null=True, blank=True)
    algoritma    = models.CharField(max_length=100, default='Decision Tree')
    dataset_size = models.IntegerField(default=0)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    catatan      = models.TextField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    created_by   = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Versi Model'
        verbose_name_plural = 'Riwayat Versi Model'

    def __str__(self):
        return f"v{self.versi} — {self.akurasi:.1%} ({self.status})"


# ─── TESTIMONI ───────────────────────────────────────────────────────────────
class Testimoni(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='testimoni')
    bintang    = models.IntegerField(default=5)  # 1-5 bintang
    ulasan     = models.TextField()
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Testimoni'
        verbose_name_plural = 'Testimoni'

    def __str__(self):
        return f"{self.user.username} — ⭐{self.bintang}"


# ─── FORUM DISKUSI ───────────────────────────────────────────────────────────
class ForumPost(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='forum_posts')
    judul      = models.CharField(max_length=200)
    konten     = models.TextField()
    kategori   = models.CharField(max_length=50, default='Umum')  # cth: Jurusan, UTBK, Karir, Umum
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Forum Post'
        verbose_name_plural = 'Forum Posts'

    def __str__(self):
        return self.judul


class ForumComment(models.Model):
    post       = models.ForeignKey(ForumPost, on_delete=models.CASCADE, related_name='comments')
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='forum_comments')
    konten     = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Forum Comment'
        verbose_name_plural = 'Forum Comments'

    def __str__(self):
        return f"Reply by {self.user.username} on {self.post.judul}"


# ─── AKTIVITAS LOG (Security) ────────────────────────────────────────────────
class AktivitasLog(models.Model):
    """Log aktivitas mencurigakan dan keamanan sistem."""
    JENIS_CHOICES = [
        ('login_gagal',    '🔐 Login Gagal'),
        ('rate_limit',     '🚫 Rate Limit Terlampaui'),
        ('akses_ditolak',  '⛔ Akses Ditolak'),
        ('captcha_gagal',  '🤖 CAPTCHA Gagal'),
        ('register_gagal', '📝 Register Gagal'),
        ('login_sukses',   '✅ Login Sukses'),
        ('logout',         '🚪 Logout'),
        ('session_timeout','⏱️ Session Timeout'),
    ]
    user       = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='aktivitas_log')
    username   = models.CharField(max_length=150, blank=True)  # simpan meski user null
    jenis      = models.CharField(max_length=30, choices=JENIS_CHOICES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    keterangan = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Log Aktivitas'
        verbose_name_plural = 'Log Aktivitas Keamanan'

    def __str__(self):
        u = self.username or (self.user.username if self.user else 'anonim')
        return f"[{self.get_jenis_display()}] {u} — {self.created_at.strftime('%d/%m %H:%M')}"

