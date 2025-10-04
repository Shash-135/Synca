# synca_project/settings.py

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# --- IMPORTANT ---
# You should load your SECRET_KEY and DEBUG status from a .env file
# for security. For now, we'll leave the defaults.
# Example: SECRET_KEY = os.environ.get('SECRET_KEY')
SECRET_KEY = 'django-insecure-your-temp-key-replace-me'
DEBUG = True

ALLOWED_HOSTS = []

# --- Application definition ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # --- Your Apps ---
    'core.apps.CoreConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'synca_project.urls'

# --- Template Configuration ---
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')], # Tells Django to look in the root templates folder
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

WSGI_APPLICATION = 'synca_project.wsgi.application'

# --- Database Configuration ---
# TODO: Replace this with your MySQL settings, preferably loaded from .env
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'synca_db',                 # The name of your database from Step 2
        'USER': 'synca_user',               # The username you created in Step 3
        'PASSWORD': 'synca123',  # The password you chose in Step 3
        'HOST': '127.0.0.1',                # Or 'localhost'
        'PORT': '3306',                     # Default MySQL port
    }
}

# --- Password validation ---
# ... default password validators

# --- Internationalization ---
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# --- Static files (CSS, JavaScript, Images) ---
STATIC_URL = 'static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# --- Default primary key field type ---
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- Custom User Model ---
# CRITICAL: Tells Django to use our custom User model
AUTH_USER_MODEL = 'core.User'