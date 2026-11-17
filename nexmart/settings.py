from pathlib import Path

import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
)
environ.Env.read_env(BASE_DIR / '.env')


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG')

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])

# Elastic Beanstalk: the load balancer health-checks instances by private IP, so allow this instance's IP too.
if not DEBUG and env.bool('ON_ELASTIC_BEANSTALK', default=False):
    try:
        import urllib.request
        _req = urllib.request.Request('http://169.254.169.254/latest/api/token', method='PUT',
                                      headers={'X-aws-ec2-metadata-token-ttl-seconds': '60'})
        _token = urllib.request.urlopen(_req, timeout=2).read().decode()
        _req = urllib.request.Request('http://169.254.169.254/latest/meta-data/local-ipv4',
                                      headers={'X-aws-ec2-metadata-token': _token})
        ALLOWED_HOSTS.append(urllib.request.urlopen(_req, timeout=2).read().decode())
    except Exception:
        pass


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    'account.apps.AccountConfig',
    "category.apps.CatregoryConfig",
    "store.apps.StoreConfig",
    "carts.apps.CartsConfig",
    "orders.apps.OrdersConfig",
    "admin_honeypot",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "nexmart.middleware.AuthenticatedSessionTimeoutMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "nexmart.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / 'templates'],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "category.context_processors.nav_categories",
                "carts.context_processors.cart_summary",
            ],
        },
    },
]

WSGI_APPLICATION = "nexmart.wsgi.application"


# Database
# https://docs.djangoproject.com/en/6.1/ref/settings/#databases

DATABASES = {
    "default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
}
# Amazon RDS PostgreSQL. Precedence: AWS_POSTGRESQL_* (.env) > RDS_* (injected by
# Elastic Beanstalk when RDS is attached) > DATABASE_URL > local sqlite.
_rds = {
    "NAME": env("AWS_POSTGRESQL_DATABASE", default="") or env("RDS_DB_NAME", default=""),
    "USER": env("AWS_POSTGRESQL_USER", default="") or env("RDS_USERNAME", default=""),
    "PASSWORD": env("AWS_POSTGRESQL_PASSWORD", default="") or env("RDS_PASSWORD", default=""),
    "HOST": env("AWS_POSTGRESQL_HOSTNAME", default="") or env("RDS_HOSTNAME", default=""),
    "PORT": env("AWS_POSTGRESQL_PORT", default="") or env("RDS_PORT", default="5432"),
}
if _rds["HOST"]:
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.postgresql",
        **_rds,
        "CONN_MAX_AGE": env.int("DB_CONN_MAX_AGE", default=60),
        "OPTIONS": {"sslmode": env("AWS_POSTGRESQL_SSLMODE", default="require")},
    }


# Password validation
# https://docs.djangoproject.com/en/6.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.1/howto/static-files/

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}
# Hashed filenames (cache busting) need collectstatic's manifest, so only enable them on the deployed server.
if env.bool("ON_ELASTIC_BEANSTALK", default=False):
    STORAGES["staticfiles"]["BACKEND"] = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Uploaded media (product images, profile photos) on Amazon S3. Elastic Beanstalk disks are ephemeral,
# so set AWS_STORAGE_BUCKET_NAME in production; the instance role needs s3:PutObject/GetObject/DeleteObject.
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="")
if AWS_STORAGE_BUCKET_NAME:
    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="ap-southeast-2")
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = False  # bucket policy must allow public read of media/*
    AWS_S3_FILE_OVERWRITE = False
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {"location": "media"},
    }
    MEDIA_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com/media/"


# Email
# https://docs.djangoproject.com/en/6.1/topics/email/#topic-email-configuration

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER


# Logging: send errors (with tracebacks) to stderr so Elastic Beanstalk captures them in web.stdout.log.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
        "django.security": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
    "root": {"handlers": ["console"], "level": "WARNING"},
}


# Celery
# https://docs.celeryq.dev/en/stable/django/first-steps-with-django.html

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
if CELERY_BROKER_URL.startswith("sqs://"):
    # Amazon SQS broker (production). Credentials come from the instance role, never from the URL.
    # SQS cannot store task results, and the app never reads them.
    CELERY_BROKER_TRANSPORT_OPTIONS = {
        "region": env("AWS_S3_REGION_NAME", default="ap-southeast-2"),
        "queue_name_prefix": env("CELERY_QUEUE_PREFIX", default="nexmart-"),
        "visibility_timeout": 300,
        "polling_interval": 5,
    }
    CELERY_RESULT_BACKEND = None
else:
    CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=CELERY_BROKER_URL)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE


AUTH_USER_MODEL = "account.User"

# Authentication
# https://docs.djangoproject.com/en/6.1/topics/auth/default/

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"

# PayPal (sandbox by default). Credentials come from .env.
PAYPAL_CLIENT_ID = env("PAYPAL_CLIENT_ID", default="")
PAYPAL_SECRET_KEY = env("PAYPAL_SECRET_KEY", default="")
PAYPAL_API_BASE = env("PAYPAL_API_BASE", default="https://api-m.sandbox.paypal.com")
PAYPAL_CURRENCY = env("PAYPAL_CURRENCY", default="USD")


# Admin security: /admin/ is a honeypot (fake login that logs attempts); the real admin lives at a secret path.
ADMIN_URL = env("ADMIN_URL", default="").strip("/")
if not ADMIN_URL and not DEBUG:
    raise RuntimeError("Set ADMIN_URL in the environment to a hard-to-guess path (e.g. ADMIN_URL=my-secret-panel).")
ADMIN_URL = ADMIN_URL or "manage-admin"
ADMIN_HONEYPOT_EMAIL_ADMINS = env.bool("ADMIN_HONEYPOT_EMAIL_ADMINS", default=False)


# Log users out after 15 minutes of inactivity (django-session-timeout; logged-in users only).
SESSION_EXPIRE_SECONDS = 900
SESSION_EXPIRE_AFTER_LAST_ACTIVITY = True
SESSION_TIMEOUT_REDIRECT = 'login'  # None -> LOGIN_URL with ?next=


# Production hardening (behind the Elastic Beanstalk load balancer).
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])  # e.g. https://shop.example.com
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    # Turn on once the load balancer has an HTTPS listener (ACM certificate); otherwise logins break over http.
    USE_HTTPS = env.bool("USE_HTTPS", default=False)
    SESSION_COOKIE_SECURE = USE_HTTPS
    CSRF_COOKIE_SECURE = USE_HTTPS
    SECURE_SSL_REDIRECT = USE_HTTPS
    SECURE_REDIRECT_EXEMPT = [r"^health/$"]
    SECURE_HSTS_SECONDS = 31536000 if USE_HTTPS else 0
    SECURE_CONTENT_TYPE_NOSNIFF = True
