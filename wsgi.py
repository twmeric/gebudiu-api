"""
WSGI Entry Point for GeBuDiu API
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

# 导入应用
from app_secure import app

if __name__ == '__main__':
    app.run()
