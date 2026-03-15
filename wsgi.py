"""
WSGI Entry Point for GeBuDiu API - Enhanced v3.0
Auto-detects and uses enhanced features if available
"""
import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(__file__))

# Try to use enhanced version first
try:
    from app_enhanced import app
    logger.info("✅ Enhanced Translation Service loaded (v3.0)")
    logger.info("   Features: Translation Memory + Domain Detection")
except ImportError as e:
    logger.warning(f"⚠️ Enhanced features not available: {e}")
    logger.info("   Falling back to standard service (v2.0)")
    from app_secure import app

if __name__ == '__main__':
    app.run()
