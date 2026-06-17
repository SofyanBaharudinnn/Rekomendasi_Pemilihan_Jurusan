"""
rekomendasi/security.py
Helper functions: Math CAPTCHA, Rate Limiting, Activity Logging
"""
import random
import hashlib
import time
from django.core.cache import cache
from django.utils import timezone


# ═══════════════════════════════════════════════════════════════════════════════
#  MATH CAPTCHA
# ═══════════════════════════════════════════════════════════════════════════════

def generate_captcha():
    """
    Generate soal CAPTCHA matematika sederhana.
    Returns dict: {'soal': '7 + 3', 'answer': 10, 'token': 'abc123...'}
    """
    a = random.randint(1, 15)
    b = random.randint(1, 15)
    ops = [
        ('+', a + b),
        ('-', a - b if a >= b else b - a),
        ('×', a * b),
    ]
    # Pilih operasi random, tapi pastikan tidak minus
    if a < b:
        a, b = b, a  # swap agar selalu a >= b
    op_sym, answer = random.choice(ops[:2])  # hanya + dan - untuk kemudahan

    soal = f"{a} {op_sym} {b}"
    # token untuk binding ke session
    token = hashlib.md5(f"{soal}{answer}{time.time()}".encode()).hexdigest()[:12]
    return {'soal': soal, 'answer': answer, 'token': token}


def validate_captcha(session, user_answer):
    """
    Validasi jawaban CAPTCHA dari session.
    Returns (bool, str): (valid, pesan_error)
    """
    expected = session.get('captcha_answer')
    if expected is None:
        return False, 'CAPTCHA tidak ditemukan. Refresh halaman.'
    try:
        if int(user_answer) == int(expected):
            # Hapus dari session setelah berhasil (single-use)
            del session['captcha_answer']
            session.modified = True
            return True, ''
        return False, 'Jawaban CAPTCHA salah. Coba lagi.'
    except (ValueError, TypeError):
        return False, 'Jawaban CAPTCHA harus berupa angka.'


def set_captcha_session(session, answer):
    """Simpan jawaban CAPTCHA yang benar ke session."""
    session['captcha_answer'] = answer
    session.modified = True


# ═══════════════════════════════════════════════════════════════════════════════
#  RATE LIMITING (Cache-based, no Redis required)
# ═══════════════════════════════════════════════════════════════════════════════

RATE_LIMITS = {
    'predict':   {'max': 15, 'window': 60},   # 15 req / 60 detik
    'login':     {'max': 5,  'window': 60},   # 5 req / 60 detik
    'register':  {'max': 3,  'window': 60},   # 3 req / 60 detik
    'api':       {'max': 60, 'window': 60},   # 60 req / 60 detik (general API)
}

def get_client_ip(request):
    """Dapatkan IP client yang sesungguhnya (support proxy)."""
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


def check_rate_limit(request, endpoint='api'):
    """
    Cek apakah request melewati batas rate limit.
    Returns (bool, int): (is_blocked, seconds_remaining)
    Kompatibel dengan LocMemCache (tidak butuh Redis).
    """
    ip = get_client_ip(request)
    config = RATE_LIMITS.get(endpoint, RATE_LIMITS['api'])
    cache_key   = f"rl:{endpoint}:{ip}"
    block_key   = f"rl:block:{endpoint}:{ip}"
    block_ts_key = f"rl:block_ts:{endpoint}:{ip}"

    # Cek apakah sedang diblokir — gunakan timestamp, bukan .ttl()
    block_until = cache.get(block_ts_key)
    if block_until:
        remaining = int(block_until - time.time())
        if remaining > 0:
            return True, remaining
        # Blokir sudah kedaluwarsa — bersihkan
        cache.delete(block_key)
        cache.delete(block_ts_key)

    # Increment counter dalam window
    count = cache.get(cache_key, 0) + 1
    cache.set(cache_key, count, timeout=config['window'])

    if count > config['max']:
        BLOCK_SECONDS = 60
        cache.set(block_key, True, timeout=BLOCK_SECONDS)
        # Simpan timestamp kapan blokir berakhir
        cache.set(block_ts_key, time.time() + BLOCK_SECONDS, timeout=BLOCK_SECONDS + 5)
        return True, BLOCK_SECONDS

    return False, 0


def get_rate_limit_remaining(request, endpoint='api'):
    """Berapa sisa request yang boleh dilakukan."""
    ip = get_client_ip(request)
    config = RATE_LIMITS.get(endpoint, RATE_LIMITS['api'])
    cache_key = f"rl:{endpoint}:{ip}"
    count = cache.get(cache_key, 0)
    return max(0, config['max'] - count)


# ═══════════════════════════════════════════════════════════════════════════════
#  ACTIVITY LOGGER
# ═══════════════════════════════════════════════════════════════════════════════

def log_activity(request, jenis, keterangan='', user=None, username=''):
    """
    Catat aktivitas ke database AktivitasLog.
    Aman jika dipanggil dari mana saja — tidak akan raise Exception.
    """
    try:
        # Import di sini untuk hindari circular import
        from .models import AktivitasLog
        ip = get_client_ip(request)
        ua = request.META.get('HTTP_USER_AGENT', '')[:300]
        u = user or (request.user if request.user.is_authenticated else None)
        uname = username or (u.username if u else '')

        AktivitasLog.objects.create(
            user=u,
            username=uname,
            jenis=jenis,
            ip_address=ip,
            user_agent=ua,
            keterangan=keterangan,
        )
    except Exception:
        pass  # Jangan pernah crash karena logging


# ═══════════════════════════════════════════════════════════════════════════════
#  PREDICTION CACHE
# ═══════════════════════════════════════════════════════════════════════════════

PREDICT_CACHE_TIMEOUT = 30 * 60  # 30 menit


def get_predict_cache_key(mat, bhs, ipa, ips, tek, sen, bis, kes):
    """Generate cache key unik berdasarkan input prediksi."""
    raw = f"{mat}:{bhs}:{ipa}:{ips}:{tek}:{sen}:{bis}:{kes}"
    return f"predict:{hashlib.md5(raw.encode()).hexdigest()}"


def get_cached_prediction(mat, bhs, ipa, ips, tek, sen, bis, kes):
    """Ambil hasil prediksi dari cache. Return None jika tidak ada."""
    key = get_predict_cache_key(mat, bhs, ipa, ips, tek, sen, bis, kes)
    return cache.get(key)


def set_cached_prediction(mat, bhs, ipa, ips, tek, sen, bis, kes, result_data):
    """Simpan hasil prediksi ke cache."""
    key = get_predict_cache_key(mat, bhs, ipa, ips, tek, sen, bis, kes)
    cache.set(key, result_data, timeout=PREDICT_CACHE_TIMEOUT)


def invalidate_prediction_cache():
    """Invalidate semua cache prediksi (dipanggil setelah retrain)."""
    # LocMemCache tidak support pattern delete, tapi cache akan expire sendiri
    # Untuk Redis: cache.delete_pattern('predict:*')
    try:
        cache.clear()
    except Exception:
        pass
