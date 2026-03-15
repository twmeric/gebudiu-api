"""
WSGI Entry Point for GeBuDiu API
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

# Use the basic app for now
from app import app

if __name__ == '__main__':
    app.run()
