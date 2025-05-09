from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

# Clerk environment variables
CLERK_API_SECRET_KEY = os.getenv("CLERK_API_SECRET_KEY")
CLERK_PUBLISHABLE_KEY = os.getenv("CLERK_PUBLISHABLE_KEY")
CLERK_AUTHORIZED_PARTIES = os.getenv("CLERK_AUTHORIZED_PARTIES", "").split(",")
CLERK_FRONTEND_API = "https://square-alpaca-17.clerk.accounts.dev"
# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-CHANGE_THIS_FOR_PRODUCTION'
DEBUG = True
ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'corsheaders',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'clerkapp',  # your app
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # must be at top
    'django.middleware.common.CommonMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'clerkproject.urls'

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

WSGI_APPLICATION = 'clerkproject.wsgi.application'

# Database (default SQLite)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Auth
AUTHENTICATION_BACKENDS = [
    'clerkapp.auth.JwtAuthBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Timezone / localization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static
STATIC_URL = '/static/'

# Default primary key field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ✅ CORS Settings
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",  # or 5178 or 5179 based on Vite port
]
    
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'origin',
    'user-agent',
    'x-requested-with',
    'x-csrftoken',
]

# Optional: allow all for dev
CORS_ORIGIN_ALLOW_ALL = True  # not needed if using CORS_ALLOWED_ORIGINS