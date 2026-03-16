# wsgi.py - Simple entry point for Gunicorn
from app import app

# For Gunicorn
# gunicorn --bind 0.0.0.0:$PORT wsgi:app
