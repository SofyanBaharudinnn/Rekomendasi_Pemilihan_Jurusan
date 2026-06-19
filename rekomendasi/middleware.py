"""
rekomendasi/middleware.py
Custom middleware: Rate Limiting & Session Timeout
"""
import time
# pyrefly: ignore [missing-import]
from django.http import JsonResponse
# pyrefly: ignore [missing-import]
from django.shortcuts import redirect
# pyrefly: ignore [missing-import]
from django.utils import timezone
# pyrefly: ignore [missing-import]
from django.urls import reverse
from .security import check_rate_limit, log_activity, get_client_ip


# ═══════════════════════════════════════════════════════════════════════════════
#  RATE LIMIT MIDDLEWARE
# ═══════════════════════════════════════════════════════════════════════════════

# Peta endpoint URL ke nama rate-limit group
RATE_LIMIT_MAP = {
    '/predict/':      'predict',
    '/login/':        'login',
    '/register/':     'register',
}

class RateLimitMiddleware:
    """
    Middleware untuk membatasi jumlah request per IP per endpoint.
    Bekerja dengan Django's in-memory cache (tidak perlu Redis).
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # Hanya cek POST request pada endpoint sensitif
        if request.method == 'POST':
            endpoint = RATE_LIMIT_MAP.get(path)
            if endpoint:
                is_blocked, seconds = check_rate_limit(request, endpoint)
                if is_blocked:
                    # Log aktivitas mencurigakan
                    log_activity(
                        request,
                        jenis='rate_limit',
                        keterangan=f'Rate limit tercapai pada {path}. Blokir {seconds}s.',
                        username=request.POST.get('username', '')
                    )
                    # Jika JSON request
                    if request.content_type == 'application/json':
                        return JsonResponse({
                            'error': f'Terlalu banyak percobaan. Tunggu {seconds} detik.',
                            'retry_after': seconds,
                        }, status=429)
                    # Jika form biasa — set pesan di session
                    request.session['rate_limit_msg'] = (
                        f'Terlalu banyak percobaan. Tunggu {seconds} detik sebelum mencoba lagi.'
                    )
                    return redirect(path)

        # Cek rate limit umum untuk API
        if path.startswith('/api/') and request.method in ('POST', 'GET'):
            is_blocked, seconds = check_rate_limit(request, 'api')
            if is_blocked:
                log_activity(
                    request,
                    jenis='rate_limit',
                    keterangan=f'API rate limit pada {path}',
                )
                return JsonResponse({
                    'error': 'Too many requests. Please slow down.',
                    'retry_after': seconds,
                }, status=429)

        response = self.get_response(request)
        return response


# ═══════════════════════════════════════════════════════════════════════════════
#  SESSION TIMEOUT MIDDLEWARE
# ═══════════════════════════════════════════════════════════════════════════════

SESSION_TIMEOUT_SECONDS = 30 * 60  # 30 menit

# Path yang tidak perlu dicek (halaman publik)
EXEMPT_PATHS = {'/login/', '/logout/', '/register/', '/', '/static/', '/media/'}

class SessionTimeoutMiddleware:
    """
    Otomatis logout user setelah idle SESSION_TIMEOUT_SECONDS detik.
    Timer direset setiap kali ada request aktif.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Guard: hanya jalankan jika AuthenticationMiddleware sudah berjalan
        if hasattr(request, 'user') and request.user.is_authenticated:
            path = request.path

            # Skip exempt paths
            if not any(path.startswith(p) for p in EXEMPT_PATHS):
                last_activity = request.session.get('last_activity')
                now = time.time()

                if last_activity:
                    elapsed = now - last_activity
                    if elapsed > SESSION_TIMEOUT_SECONDS:
                        # Log timeout
                        log_activity(
                            request,
                            jenis='session_timeout',
                            keterangan=f'Idle {int(elapsed)}s > {SESSION_TIMEOUT_SECONDS}s',
                            user=request.user,
                        )
                        # Flush session
                        # pyrefly: ignore [missing-import]
                        from django.contrib.auth import logout
                        logout(request)
                        # Redirect ke login dengan pesan
                        login_url = reverse('login')
                        return redirect(f"{login_url}?timeout=1")

                # Update last activity timestamp
                request.session['last_activity'] = now
                request.session.modified = True

        response = self.get_response(request)
        return response
