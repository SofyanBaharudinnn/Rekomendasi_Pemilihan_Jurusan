"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os

# Konfigurasi GEMINI_API_KEY agar terbaca oleh settings.py
os.environ['GEMINI_API_KEY'] = 'AIzaSyDHZYF3ILx5geJByBywfPN5TIob36_wOcs'

# pyrefly: ignore [missing-import]
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()

