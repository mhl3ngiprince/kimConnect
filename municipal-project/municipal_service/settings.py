ALLOWED_HOSTS = ['*']

# Middlewares
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    #... (rest of your middleware)
]