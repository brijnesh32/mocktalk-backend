import os
from dotenv import load_dotenv
from pathlib import Path
import dj_database_url
from mongoengine import connect

load_dotenv()

# === BASE DIR ===
BASE_DIR = Path(__file__).resolve().parent.parent

# === SECURITY ===
SECRET_KEY = os.environ.get("SECRET_KEY", "fallback-secret-key-change-this")
DEBUG = os.environ.get("DEBUG", "False") == "True"

# FIX #1: your Render URL was wrong — was mocktalk-backend.onrender.com
# but your actual URL is mocktalk-backend-d76d.onrender.com
ALLOWED_HOSTS = [
    "mocktalk-backend-d76d.onrender.com",
    "localhost",
    "127.0.0.1",
]

# === APPS ===
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',      # must be before your apps
    'reports',
]

# === MIDDLEWARE ===
# FIX #2: CorsMiddleware MUST be before SessionMiddleware and CommonMiddleware
# FIX #3: removed duplicate STATICFILES_STORAGE conflict (was set twice)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',        # moved up — must be high
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# === URL CONFIGURATION ===
ROOT_URLCONF = 'mocktalk.urls'

# === WSGI ===
WSGI_APPLICATION = 'mocktalk.wsgi.application'

# === TEMPLATES ===
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

# === DATABASE ===
DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600
    )
}

# === MONGODB ===
# FIX #4: added error handling so missing MONGODB_URI doesn't crash the app
MONGODB_URI = os.getenv("MONGODB_URI")
if MONGODB_URI:
    connect(host=MONGODB_URI)
else:
    print("WARNING: MONGODB_URI not set — MongoDB connection skipped")

# === CORS ===
# FIX #5: replaced CORS_ALLOW_ALL_ORIGINS=True (dangerous) with explicit list
CORS_ALLOWED_ORIGINS = [
    "https://mocktalk.vercel.app",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]

# FIX #6: added CSRF trusted origins — this was causing the 400 error
CSRF_TRUSTED_ORIGINS = [
    "https://mocktalk.vercel.app",
    "https://mocktalk-backend-d76d.onrender.com",
]

# Allow these headers from the frontend
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

# === STATIC FILES ===
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# FIX #3: single STATICFILES_STORAGE definition — no conflict
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# === AUTH PASSWORD VALIDATORS ===
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# === LANGUAGE & TIME ===
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# === DEFAULT AUTO FIELD ===
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'