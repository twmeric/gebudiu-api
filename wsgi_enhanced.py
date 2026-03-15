"""
WSGI entry point for Render deployment - Enhanced version
"""
import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the enhanced app
from app_enhanced import app

# For Gunicorn
application = app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
