#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GeBuDiu API - 整合 WhatsApp 模組示例

此文件展示如何在 app_enhanced.py 中整合 WhatsApp 功能
請將相關代碼複製到實際的 app_enhanced.py 文件中
"""

# ==================== 在文件頂部添加導入 ====================

# 在原有的導入之後添加：

# WhatsApp 整合
try:
    from whatsapp_routes import init_whatsapp_routes, WHATSAPP_AVAILABLE
    WHATSAPP_ENABLED = True
except ImportError as e:
    WHATSAPP_ENABLED = False
    logging.warning(f"WhatsApp integration not available: {e}")


# ==================== 在 init_services() 函數中添加 ====================

def init_services():
    """初始化翻譯服務"""
    global translation_service, translation_memory, terminology_manager
    
    if not ENHANCED_MODE:
        logger.warning("Running in legacy mode (enhanced features disabled)")
        return
    
    try:
        # ... 原有初始化代碼 ...
        
        # 初始化 Translation Memory
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
        
        # 初始化格式自學習引擎
        if FORMAT_LEARNING_AVAILABLE:
            format_engine = get_format_learning_engine()
            logger.info("Format Learning Engine initialized (GBD USP)")
        
        # ============ 初始化 WhatsApp 整合 ============
        if WHATSAPP_ENABLED:
            try:
                init_whatsapp_routes(app)
                logger.info("✅ WhatsApp integration initialized")
                
                # 添加 WhatsApp 狀態到健康檢查
                app.config['WHATSAPP_ENABLED'] = True
            except Exception as e:
                logger.error(f"Failed to initialize WhatsApp: {e}")
                app.config['WHATSAPP_ENABLED'] = False
        else:
            logger.info("WhatsApp integration disabled (module not available)")
            app.config['WHATSAPP_ENABLED'] = False
        
    except Exception as e:
        logger.error(f"Failed to initialize enhanced services: {e}")
        logger.info("Falling back to legacy mode")


# ==================== 更新 health() 端點 ====================

@app.route('/health', methods=['GET'])
def health():
    """健康檢查"""
    status = {
        "status": "ok",
        "service": "格不丢翻译 API - Enhanced",
        "version": "3.1.0",  # 更新版本號
        "enhanced_mode": ENHANCED_MODE,
        "timestamp": datetime.now().isoformat()
    }
    
    if ENHANCED_MODE and translation_service:
        status["features"] = {
            "translation_memory": True,
            "domain_detection": True,
            "quality_scoring": True,
            "terminology_management": True,
            "format_learning": FORMAT_LEARNING_AVAILABLE,
            "whatsapp_integration": app.config.get('WHATSAPP_ENABLED', False)  # 添加 WhatsApp 狀態
        }
        status["stats"] = translation_service.get_stats_report()
        
        # 添加格式學習狀態
        if FORMAT_LEARNING_AVAILABLE:
            try:
                format_engine = get_format_learning_engine()
                format_stats = format_engine.get_learning_stats()
                status["format_learning"] = {
                    "status": "active",
                    "tagline": "每一翻譯，都讓下一個更完美",
                    "patterns_learned": format_stats.get("total_patterns", 0),
                    "optimizations_made": format_stats.get("total_optimizations", 0)
                }
            except:
                status["format_learning"] = {"status": "initializing"}
        
        # 添加 WhatsApp 狀態詳情
        if app.config.get('WHATSAPP_ENABLED'):
            try:
                from whatsapp_module import get_whatsapp_service
                wa_service = get_whatsapp_service()
                wa_stats = wa_service.get_stats()
                status["whatsapp"] = {
                    "enabled": True,
                    "provider": wa_stats.get("provider", "unknown"),
                    "total_users": wa_stats.get("total_users", 0),
                    "verified_users": wa_stats.get("verified_users", 0)
                }
            except Exception as e:
                status["whatsapp"] = {
                    "enabled": True,
                    "error": str(e)
                }
        else:
            status["whatsapp"] = {"enabled": False}
    
    return jsonify(status)


# ==================== 可選：添加 WhatsApp 分享按鈕到翻譯響應 ====================

# 如果您希望在翻譯完成的響應中包含 WhatsApp 分享鏈接，可以修改 translate() 函數：

@app.route('/translate', methods=['POST'])
@limiter.limit("10 per minute")
def translate():
    """
    翻譯文件 - 增強版（含 WhatsApp 分享選項）
    """
    import time
    start_time = time.time()
    
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"), 400
        
        file = request.files['file']
        domain = request.form.get('domain', 'general')
        
        # 檢查是否請求 WhatsApp 分享
        whatsapp_share = request.form.get('whatsapp_share') == 'true'
        user_phone = request.form.get('user_phone')  # 用於 WhatsApp 分享
        
        if domain not in DOMAINS:
            return jsonify({"error": "Invalid domain"}), 400
        
        is_valid, error_msg, file_info = validate_file(file)
        if not is_valid:
            logger.warning(f"File validation failed: {error_msg}")
            return jsonify({"error": error_msg}), 400
        
        file_size_mb = file_info["size"] / 1024 / 1024
        if file_size_mb > 3:
            logger.warning(f"Large file ({file_size_mb:.1f}MB), processing may take time")
        
        # 使用增強服務處理
        if ENHANCED_MODE and translation_service:
            output, stats = process_with_enhanced_service(file_info, domain)
        else:
            return jsonify({"error": "Enhanced mode required"}), 503
        
        processing_time = time.time() - start_time
        
        # 如果需要 WhatsApp 分享，生成分享記錄
        share_info = None
        if whatsapp_share and WHATSAPP_ENABLED and user_phone:
            try:
                from whatsapp_module import get_whatsapp_service
                wa_service = get_whatsapp_service()
                
                # 先驗證用戶
                user = wa_service.get_user_by_phone(user_phone)
                if user and user.verified:
                    # 生成臨時下載鏈接
                    share_link = generate_temp_download_link(file_info)
                    
                    # 記錄分享
                    share_result = wa_service.share_file(
                        user_phone=user_phone,
                        file_info={
                            'name': file_info['filename'].replace(file_info['extension'], f'_EN{file_info["extension"]}'),
                            'type': file_info['extension'].replace('.', ''),
                            'size': file_info['size']
                        },
                        share_type='self',
                        share_link=share_link
                    )
                    
                    if share_result.get('success'):
                        share_info = {
                            "shared": True,
                            "share_id": share_result.get('share_id'),
                            "share_link": share_link
                        }
            except Exception as e:
                logger.error(f"WhatsApp share failed: {e}")
        
        logger.info(f"Translation completed: {file_info['filename']}, time: {processing_time:.2f}s")
        
        # 構建響應
        response = make_response(send_file(
            output,
            mimetype=get_mimetype(file_info["extension"]),
            as_attachment=True,
            download_name=file_info['filename'].replace(file_info["extension"], f'_EN{file_info["extension"]}')
        ))
        
        # 添加響應頭
        response.headers['X-Processing-Time'] = f"{processing_time:.2f}"
        if stats:
            response.headers['X-API-Calls'] = str(stats.get("api_calls", 0))
            response.headers['X-TM-Hits'] = str(stats.get("tm_hits", 0))
            response.headers['X-Cache-Hits'] = str(stats.get("cache_hits", 0))
            response.headers['X-Domain'] = stats.get("domain", domain)
        
        # 如果 WhatsApp 分享成功，添加自定義頭
        if share_info:
            response.headers['X-WhatsApp-Shared'] = 'true'
            response.headers['X-Share-ID'] = str(share_info.get('share_id', ''))
        
        return response
        
    except Exception as e:
        logger.error(f"Translation failed: {e}", exc_info=True)
        return jsonify({
            "error": "Translation failed",
            "message": str(e)
        }), 500


def generate_temp_download_link(file_info: dict) -> str:
    """
    生成臨時下載鏈接
    這是一個示例實現，實際應根據您的文件存儲方式實現
    """
    import hashlib
    import secrets
    
    # 生成臨時 token
    token = secrets.token_urlsafe(32)
    
    # 構建鏈接
    base_url = os.getenv('FRONTEND_URL', 'https://gebudiu.io')
    return f"{base_url}/download/{token}?file={file_info['filename']}"


# ==================== 添加 WhatsApp 分享歷史 API ====================

# 這個端點已經在 whatsapp_routes.py 中定義，這裡僅作為參考

# GET /whatsapp/share/history - 獲取分享歷史
# POST /whatsapp/share - 分享文件
# 等等...


# ==================== 啟動應用 ====================

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    
    # 打印 WhatsApp 整合狀態
    if WHATSAPP_ENABLED:
        print("✅ WhatsApp integration: ENABLED")
        print(f"   Provider: {os.getenv('WHATSAPP_PROVIDER', 'mock')}")
    else:
        print("⚠️  WhatsApp integration: DISABLED")
    
    app.run(debug=False, host='0.0.0.0', port=port)
