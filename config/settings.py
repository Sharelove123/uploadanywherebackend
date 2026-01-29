"""
Django settings for Content Repurposer project.
"""
import os
from pathlib import Path
from datetime import timedelta

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-change-this-in-production-use-env-var')

# Handle Render's PORT environment variable
PORT = os.environ.get('PORT', '8000')

FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True # os.environ.get('DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS = ['*']


import dj_database_url

# Application definition
SHARED_APPS = [
    'django_tenants',  # mandatory
    'apps.tenants',    # your tenant app

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',  # Required for dj-rest-auth
    
    # Third-party apps (Shared)
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'dj_rest_auth',
    'corsheaders',

    # Shared apps
    'apps.payments',  # SubscriptionPlans are shared
    'apps.users',     # User model needed for admin
]

TENANT_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.messages',
    
    # Allauth (Tenant-level because User is tenant-level)
    'allauth',
    'allauth.account',
    'allauth.socialaccount',

    # Auth Tokens (Must be tenant-level if Users are)
    'rest_framework.authtoken',
    'rest_framework_simplejwt.token_blacklist',
    
    # Tenant-specific apps
    'apps.users',
    'apps.teams',
    'apps.repurposer',
    'apps.social_accounts',
    # Note: apps.payments moved to SHARED_APPS only (SubscriptionPlan is global)
]

INSTALLED_APPS = list(SHARED_APPS) + [app for app in TENANT_APPS if app not in SHARED_APPS]

TENANT_MODEL = "tenants.Client"  # app.Model
TENANT_DOMAIN_MODEL = "tenants.Domain"  # app.Model

# Required for dj-rest-auth
SITE_ID = 1

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'apps.tenants.middleware.HeaderTenantMiddleware',  # Custom middleware for Render/Vercel support
    'django.middleware.security.SecurityMiddleware',
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Add Whitenoise for static files
    
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'config.urls_tenant'
PUBLIC_SCHEMA_URLCONF = 'config.urls_public'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# Database
DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL', f"postgres://{os.environ.get('DB_USER', 'postgres')}:{os.environ.get('DB_PASSWORD', 'abcd')}@{os.environ.get('DB_HOST', 'localhost')}:{os.environ.get('DB_PORT', '5432')}/{os.environ.get('DB_NAME', 'abcd')}"),
        conn_max_age=600,
        engine='django_tenants.postgresql_backend'
    )
}
DATABASE_ROUTERS = (
    'django_tenants.routers.TenantSyncRouter',
)


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Allauth Configuration
# Allauth Configuration
# ACCOUNT_LOGIN_METHODS = {'email', 'username'}  # Commented out to resolve conflict warning
# ACCOUNT_EMAIL_REQUIRED = True  # Deprecated, handled by ACCOUNT_SIGNUP_FIELDS

ACCOUNT_AUTHENTICATION_METHOD = 'username_email' # Traditional way, safe for now
ACCOUNT_EMAIL_VERIFICATION = 'optional'
ACCOUNT_CONFIRM_EMAIL_ON_GET = True

ACCOUNT_SIGNUP_FIELDS = [
    'email',
    'username',
]


# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# Static files
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'users.CustomUser'


# ==============================================================================
# EMAIL SETTINGS
# ==============================================================================
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'webmaster@localhost')


# ==============================================================================
# CORS SETTINGS
# ==============================================================================
# CORS Settings
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True

if os.environ.get('CORS_ALLOWED_ORIGINS'):
    CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS').split(',')
else:
    CORS_ALLOWED_ORIGINS = [
        'http://localhost:3000',
        'http://127.0.0.1:3000',
        'http://lvh.me:3000',
    ]

CORS_ALLOWED_ORIGIN_REGEXES = [
    r'^http://.*\.localhost:3000$',
    r'^http://.*\.lvh\.me:3000$',  # Allow all lvh.me subdomains
    r'^https://.*\.vercel\.app$',  # Allow all Vercel subdomains (simplified)
]

# Allow custom headers (including our X-Tenant-Domain header)
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'x-tenant-domain',  # Our custom header for tenant routing
]

# CSRF Settings
if os.environ.get('CORS_ALLOWED_ORIGINS'):
    CSRF_TRUSTED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS').split(',')
else:
    CSRF_TRUSTED_ORIGINS = [
        'http://localhost:3000',
        'http://127.0.0.1:3000',
        'http://*.localhost:3000',
        'http://*.lvh.me:3000',
        'http://lvh.me:3000',
    ]
CSRF_COOKIE_SAMESITE = 'None'
CSRF_COOKIE_HTTPONLY = False  # Allow JS to read for AJAX
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_DOMAIN = os.environ.get('COOKIE_DOMAIN', None)
SESSION_COOKIE_DOMAIN = os.environ.get('COOKIE_DOMAIN', None)
SESSION_COOKIE_SAMESITE = 'None'
SESSION_COOKIE_SECURE = True



# ==============================================================================
# REST FRAMEWORK SETTINGS
# ==============================================================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication', 
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}


# ==============================================================================
# JWT SETTINGS (Simple JWT)
# ==============================================================================
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}


# ==============================================================================
# DJ-REST-AUTH SETTINGS
# ==============================================================================
REST_AUTH = {
    'USE_JWT': True,
    'JWT_AUTH_COOKIE': 'auth-token',
    'JWT_AUTH_REFRESH_COOKIE': 'refresh-token',
    'JWT_AUTH_HTTPONLY': True,
    'USER_DETAILS_SERIALIZER': 'apps.users.serializers.UserProfileSerializer',
}


# ==============================================================================
# AI SETTINGS (GEMINI)
# ==============================================================================
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
GEMINI_MODEL = 'gemini-1.5-flash'


# ==============================================================================
# EMAIL SETTINGS
# ==============================================================================
# Print emails to console for now (until SMTP is set up)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'noreply@uploadanywhere.com'

# ==============================================================================
# SOCIAL OAUTH SETTINGS
# ==============================================================================
LINKEDIN_CLIENT_ID = os.environ.get('LINKEDIN_CLIENT_ID', '')
LINKEDIN_CLIENT_SECRET = os.environ.get('LINKEDIN_CLIENT_SECRET', '')
LINKEDIN_REDIRECT_URI = os.environ.get('LINKEDIN_REDIRECT_URI', 'http://localhost:3000/callback/linkedin')

TWITTER_API_KEY = os.environ.get('TWITTER_API_KEY', '')
TWITTER_API_SECRET = os.environ.get('TWITTER_API_SECRET', '')
TWITTER_REDIRECT_URI = os.environ.get('TWITTER_REDIRECT_URI', 'http://localhost:3000/callback/twitter')
TWITTER_CLIENT_ID = os.environ.get('TWITTER_CLIENT_ID', '')
TWITTER_CLIENT_SECRET = os.environ.get('TWITTER_CLIENT_SECRET', '')

GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', f"{FRONTEND_URL}/callback/youtube")

FACEBOOK_APP_ID = os.environ.get('FACEBOOK_APP_ID', '')
FACEBOOK_APP_SECRET = os.environ.get('FACEBOOK_APP_SECRET', '')
FACEBOOK_REDIRECT_URI = os.environ.get('FACEBOOK_REDIRECT_URI', f"{FRONTEND_URL}/callback/instagram")


# ==============================================================================
# STRIPE SETTINGS
# ==============================================================================
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')


# ==============================================================================
# SUBSCRIPTION LIMITS
# ==============================================================================
SUBSCRIPTION_LIMITS = {
    'free': {
        'repurposes_per_month': 2,
        'brand_voices': 0,
        'direct_posting': False,
        'platforms': ['linkedin'],
    },
    'pro': {
        'repurposes_per_month': 50,
        'brand_voices': 3,
        'direct_posting': True,
        'platforms': ['linkedin', 'twitter', 'youtube', 'instagram'],
    },
    'agency': {
        'repurposes_per_month': -1,  # Unlimited
        'brand_voices': -1,  # Unlimited
        'direct_posting': True,
        'platforms': ['linkedin', 'twitter', 'youtube', 'instagram'],
    },
}
  
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': str(BASE_DIR / 'debug.log'),
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
} 

# ==============================================================================
# SUBSCRIPTION LIMITS (Used for credit tracking)
# ==============================================================================
SUBSCRIPTION_LIMITS = {
    'free': {
        'repurposes_per_month': 5,
        'brand_voices_limit': 1,
        'direct_posting': False,
        'priority_support': False,
    },
    'pro': {
        'repurposes_per_month': 50,
        'brand_voices_limit': 5,
        'direct_posting': True,
        'priority_support': False,
    },
    'agency': {
        'repurposes_per_month': -1,  # Unlimited
        'brand_voices_limit': -1,    # Unlimited
        'direct_posting': True,
        'priority_support': True,
    },
}


# ==============================================================================
# CELERY SETTINGS (Upstash Redis)
# ==============================================================================
CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = CELERY_BROKER_URL

# Handle SSL for Upstash Redis (uses rediss:// protocol)
if CELERY_BROKER_URL.startswith('rediss://'):
    CELERY_BROKER_USE_SSL = {'ssl_cert_reqs': None}
    CELERY_REDIS_BACKEND_USE_SSL = {'ssl_cert_reqs': None}

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
