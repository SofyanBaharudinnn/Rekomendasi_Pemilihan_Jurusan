"""
Django settings for JurusanKu ID project.
"""

from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# ═══════════════════════════════════════════════════════════════════════════════
#  CORE SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-9ah5s_qe%k!#th)6_nvso6__3=3nv9drdon(+y6emgi8fma9!h'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']


# ═══════════════════════════════════════════════════════════════════════════════
#  APPLICATIONS
# ═══════════════════════════════════════════════════════════════════════════════

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rekomendasi',
]


# ═══════════════════════════════════════════════════════════════════════════════
#  MIDDLEWARE — urutan penting!
# ═══════════════════════════════════════════════════════════════════════════════

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',          # Static file compression
    'rekomendasi.middleware.RateLimitMiddleware',          # Rate limiting (tidak butuh user)
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'rekomendasi.middleware.SessionTimeoutMiddleware',     # Setelah Auth — butuh request.user
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# ═══════════════════════════════════════════════════════════════════════════════
#  DATABASE
# ═══════════════════════════════════════════════════════════════════════════════

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# ═══════════════════════════════════════════════════════════════════════════════
#  CACHE — In-Memory (LocMemCache)
#  Untuk production dengan Redis: ganti ke django.core.cache.backends.redis.RedisCache
# ═══════════════════════════════════════════════════════════════════════════════

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'jurusanku-cache',
        'TIMEOUT': 300,          # Default 5 menit
        'OPTIONS': {
            'MAX_ENTRIES': 2000,
        }
    }
}

# Untuk Redis (uncomment jika Redis tersedia):
# CACHES = {
#     'default': {
#         'BACKEND': 'django.core.cache.backends.redis.RedisCache',
#         'LOCATION': 'redis://127.0.0.1:6379/1',
#         'TIMEOUT': 300,
#     }
# }


# ═══════════════════════════════════════════════════════════════════════════════
#  SESSION
# ═══════════════════════════════════════════════════════════════════════════════

SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 1800           # 30 menit (detik) — expired jika tidak aktif
SESSION_SAVE_EVERY_REQUEST = True   # Reset timer setiap request aktif
SESSION_COOKIE_HTTPONLY = True      # Tidak bisa diakses JavaScript
SESSION_COOKIE_SAMESITE = 'Lax'    # CSRF protection


# ═══════════════════════════════════════════════════════════════════════════════
#  SECURITY HEADERS (production-ready)
# ═══════════════════════════════════════════════════════════════════════════════

X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True


# ═══════════════════════════════════════════════════════════════════════════════
#  EMAIL (Console backend untuk development — ganti ke SMTP untuk production)
# ═══════════════════════════════════════════════════════════════════════════════

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Untuk Gmail SMTP (isi saat production):
# EMAIL_BACKEND    = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST       = 'smtp.gmail.com'
# EMAIL_PORT       = 587
# EMAIL_USE_TLS    = True
# EMAIL_HOST_USER  = 'your-email@gmail.com'
# EMAIL_HOST_PASSWORD = 'your-app-password'
# DEFAULT_FROM_EMAIL = 'JurusanKu ID <your-email@gmail.com>'

DEFAULT_FROM_EMAIL = 'JurusanKu ID <noreply@jurusanku.id>'


# OAuth configurations have been removed. Refer to views.py/urls.py for login methods.


# ═══════════════════════════════════════════════════════════════════════════════
#  PASSWORD VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ═══════════════════════════════════════════════════════════════════════════════
#  INTERNATIONALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

LANGUAGE_CODE = 'id-id'
TIME_ZONE = 'Asia/Makassar'
USE_I18N = True
USE_TZ = True


# ═══════════════════════════════════════════════════════════════════════════════
#  STATIC & MEDIA FILES
# ═══════════════════════════════════════════════════════════════════════════════

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise: compress & cache static files otomatis
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# ═══════════════════════════════════════════════════════════════════════════════
#  AUTH SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ═══════════════════════════════════════════════════════════════════════════════
#  GEMINI API CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════
import os
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")