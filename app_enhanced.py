#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
格不丢翻译 API - 增強版 (v3.0)
集成 Translation Memory + 智能領域檢測

新特性:
- Translation Memory (FAISS + SQLite)
- 自動領域檢測
- 翻譯質量評分
- API成本降低 50-70%
"""

import os
import sys
import logging
from io import BytesIO
from datetime import datetime

from flask import Flask, request, send_file, jsonify, make_response
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

# 導入增強組件
try:
    from enhanced_translation_service import EnhancedTranslationService, TranslationResult
    from translation_memory import TranslationMemory
    from domain_detector import DomainDetector
    from terminology_manager import TerminologyManager, get_terminology_manager
    from terminology_api import init_terminology_routes
    ENHANCED_MODE = True
except ImportError as e:
    ENHANCED_MODE = False
    logging.warning(f"Enhanced modules not available: {e}")
    # 回退到舊版
    from app_secure import app as old_app

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('translation_enhanced.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 創建應用
app = Flask(__name__)

# CORS配置
CORS(app, origins="*", supports_credentials=False)

@app.after_request
def after_request(response):
    """為所有響應添加 CORS 頭"""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# 速率限制
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# 配置文件
MAX_FILE_SIZE = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = {'.docx', '.xlsx'}

# 领域配置
DOMAINS = {
    "general": {"name": "通用领域", "name_en": "General", "icon": "📋"},
    "electronics": {"name": "电子产品", "name_en": "Electronics", "icon": "🔌"},
    "medical": {"name": "医疗器械", "name_en": "Medical", "icon": "🏥"},
    "legal": {"name": "法律合同", "name_en": "Legal", "icon": "⚖️"},
    "marketing": {"name": "市场营销", "name_en": "Marketing", "icon": "📢"},
    "industrial": {"name": "工业技术", "name_en": "Industrial", "icon": "🏭"},
    "software": {"name": "软件/IT", "name_en": "Software", "icon": "💻"}
}

# 全局服務實例
translation_service = None
translation_memory = None
terminology_manager = None

def init_services():
    """初始化翻譯服務"""
    global translation_service, translation_memory, terminology_manager
    
    if not ENHANCED_MODE:
        logger.warning("Running in legacy mode (enhanced features disabled)")
        return
    
    try:
        # 初始化Translation Memory
        translation_memory = TranslationMemory()
        logger.info("Translation Memory initialized")
        
        # 初始化術語表管理器
        terminology_manager = get_terminology_manager()
        logger.info("Terminology Manager initialized")
        
        # 初始化增強翻譯服務
        translation_service = EnhancedTranslationService(
            domain="general",
            use_tm=True,
            tm_threshold=0.85,
            auto_detect_domain=True,
            use_terminology=True
        )
        logger.info("Enhanced Translation Service initialized")
        
        # 初始化術語表API路由
        init_terminology_routes(app, terminology_manager)
        
    except Exception as e:
        logger.error(f"Failed to initialize enhanced services: {e}")
        logger.info("Falling back to legacy mode")

def validate_file(file_storage):
    """验证上传文件"""
    if not file_storage or not getattr(file_storage, 'filename', None):
        return False, "No file selected", None
    
    filename = os.path.basename(file_storage.filename)
    ext = os.path.splitext(filename)[1].lower()
    
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}", None
    
    try:
        file_buffer = file_storage.read()
        file_storage.seek(0)
    except Exception as e:
        logger.error(f"Failed to read file: {e}")
        return False, "Failed to read uploaded file", None
    
    if len(file_buffer) == 0:
        return False, "File is empty", None
    
    if len(file_buffer) > MAX_FILE_SIZE:
        max_mb = MAX_FILE_SIZE / 1024 / 1024
        return False, f"File too large. Maximum size: {max_mb}MB", None
    
    # ZIP格式檢查
    header = file_buffer[:4]
    valid_zip_headers = [b'PK\x03\x04', b'PK\x05\x06', b'PK\x07\x08']
    if header not in valid_zip_headers:
        logger.warning(f"Invalid file header: {header.hex()}")
        return False, f"Invalid file format. Please upload a valid .docx or .xlsx file", None
    
    return True, None, {
        "filename": filename,
        "extension": ext,
        "size": len(file_buffer),
        "buffer": file_buffer
    }

def should_translate(text):
    """判斷文本是否需要翻譯"""
    if not text or len(text.strip()) < 2:
        return False
    text = text.strip()
    if text.isdigit():
        return False
    if text.startswith(('http://', 'https://')):
        return False
    return True

# API 路由
@app.route('/health', methods=['GET'])
def health():
    """健康檢查"""
    status = {
        "status": "ok",
        "service": "格不丢翻译 API - Enhanced",
        "version": "3.0.0",
        "enhanced_mode": ENHANCED_MODE,
        "timestamp": datetime.now().isoformat()
    }
    
    if ENHANCED_MODE and translation_service:
        status["features"] = {
            "translation_memory": True,
            "domain_detection": True,
            "quality_scoring": True,
            "terminology_management": True
        }
        status["stats"] = translation_service.get_stats_report()
    
    return jsonify(status)

@app.route('/domains', methods=['GET'])
def get_domains():
    """獲取支持的領域列表"""
    return jsonify({
        "domains": {
            k: {"name": v["name"], "name_en": v["name_en"], "icon": v["icon"]}
            for k, v in DOMAINS.items()
        }
    })

@app.route('/translate', methods=['POST'])
@limiter.limit("10 per minute")
def translate():
    """
    翻譯文件 - 增強版
    
    Form參數:
    - file: 要上傳的文件
    - domain: 領域 (可選, 默認自動檢測)
    - format: 輸出格式 (保留)
    """
    import time
    start_time = time.time()
    
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        domain = request.form.get('domain', 'general')
        
        if domain not in DOMAINS:
            return jsonify({"error": "Invalid domain"}), 400
        
        is_valid, error_msg, file_info = validate_file(file)
        if not is_valid:
            logger.warning(f"File validation failed: {error_msg}")
            return jsonify({"error": error_msg}), 400
        
        file_size_mb = file_info["size"] / 1024 / 1024
        if file_size_mb > 3:
            logger.warning(f"Large file ({file_size_mb:.1f}MB), processing may take time")
        
        # 使用增強服務或回退到舊版
        if ENHANCED_MODE and translation_service:
            output, stats = process_with_enhanced_service(file_info, domain)
        else:
            output, stats = process_with_legacy_service(file_info, domain)
        
        processing_time = time.time() - start_time
        
        logger.info(f"Translation completed: {file_info['filename']}, time: {processing_time:.2f}s")
        
        # 構建響應
        response = make_response(send_file(
            output,
            mimetype=get_mimetype(file_info["extension"]),
            as_attachment=True,
            download_name=file_info["filename"].replace(file_info["extension"], f'_EN{file_info["extension"]}')
        ))
        
        response.headers['X-Processing-Time'] = f"{processing_time:.2f}"
        if stats:
            response.headers['X-API-Calls'] = str(stats.get("api_calls", 0))
            response.headers['X-TM-Hits'] = str(stats.get("tm_hits", 0))
            response.headers['X-Cache-Hits'] = str(stats.get("cache_hits", 0))
            response.headers['X-Domain'] = stats.get("domain", domain)
        
        return response
        
    except Exception as e:
        logger.error(f"Translation failed: {e}", exc_info=True)
        return jsonify({
            "error": "Translation failed",
            "message": str(e)
        }), 500

def process_with_enhanced_service(file_info, domain):
    """使用增強服務處理文件"""
    from enhanced_docx_processor import EnhancedDocxProcessor
    
    # 更新服務領域
    translation_service.domain = domain
    
    if file_info["extension"] == '.docx':
        processor = EnhancedDocxProcessor(translation_service)
        output = processor.process(file_info["buffer"], file_info["filename"])
    else:
        # XLSX處理
        from openpyxl import load_workbook
        wb = load_workbook(BytesIO(file_info["buffer"]))
        
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            for row in ws.iter_rows():
                for cell in row:
                    if cell.value and isinstance(cell.value, str):
                        if should_translate(cell.value):
                            translated, is_tm = translation_service.translate_text(cell.value)
                            cell.value = translated
        
        output = BytesIO()
        wb.save(output)
        output.seek(0)
    
    stats = translation_service.get_stats_report()
    return output, stats

def process_with_legacy_service(file_info, domain):
    """回退到舊版服務"""
    # 這裡可以調用舊版處理邏輯
    # 暫時拋出錯誤，提示使用新版
    raise Exception("Enhanced mode required. Please check dependencies.")

def get_mimetype(extension):
    """獲取MIME類型"""
    if extension == '.docx':
        return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    else:
        return 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

@app.route('/tm/stats', methods=['GET'])
def tm_stats():
    """Translation Memory 統計"""
    if not ENHANCED_MODE or not translation_memory:
        return jsonify({"error": "Translation Memory not available"}), 503
    
    try:
        stats = translation_memory.get_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Failed to get TM stats: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/tm/search', methods=['POST'])
def tm_search():
    """搜索Translation Memory"""
    if not ENHANCED_MODE or not translation_memory:
        return jsonify({"error": "Translation Memory not available"}), 503
    
    try:
        data = request.get_json()
        query = data.get('query', '')
        domain = data.get('domain')
        
        if not query:
            return jsonify({"error": "Query is required"}), 400
        
        results = translation_memory.search(query, domain)
        
        return jsonify({
            "query": query,
            "results": [
                {
                    "source": r.source,
                    "target": r.target,
                    "similarity": r.similarity,
                    "domain": r.domain,
                    "hit_count": r.hit_count
                }
                for r in results
            ]
        })
        
    except Exception as e:
        logger.error(f"TM search failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/detect-domain', methods=['POST'])
def detect_domain():
    """檢測文檔領域"""
    if not ENHANCED_MODE:
        return jsonify({"error": "Domain detection not available"}), 503
    
    try:
        data = request.get_json()
        filename = data.get('filename', '')
        samples = data.get('samples', [])
        
        detector = DomainDetector()
        domain, confidence = detector.detect(filename, samples)
        info = detector.get_domain_info(domain)
        
        return jsonify({
            "domain": domain,
            "confidence": confidence,
            "info": info
        })
        
    except Exception as e:
        logger.error(f"Domain detection failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({
        "error": "Rate limit exceeded",
        "message": "Too many requests. Please try again later."
    }), 429

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal error: {e}", exc_info=True)
    return jsonify({
        "error": "Internal server error",
        "message": "Something went wrong. Please try again later."
    }), 500

# 初始化
init_services()

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
