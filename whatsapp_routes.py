#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WhatsApp 整合路由 - Flask Blueprint
為 GeBuDiu 翻譯服務提供 WhatsApp API 端點
"""

import os
import logging
from functools import wraps

from flask import Blueprint, request, jsonify, current_app

# 導入 WhatsApp 模組
try:
    from whatsapp_module import get_whatsapp_service, WhatsAppService
    WHATSAPP_AVAILABLE = True
except ImportError as e:
    WHATSAPP_AVAILABLE = False
    logging.warning(f"WhatsApp module not available: {e}")

logger = logging.getLogger(__name__)

# 創建 Blueprint
whatsapp_bp = Blueprint('whatsapp', __name__, url_prefix='/whatsapp')

# ============ 輔助函數 ============

def get_service() -> WhatsAppService:
    """獲取 WhatsApp 服務實例"""
    if not WHATSAPP_AVAILABLE:
        raise RuntimeError("WhatsApp module not available")
    return get_whatsapp_service()

def require_verified_user(f):
    """裝飾器：要求用戶已驗證"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        phone = request.headers.get('X-User-Phone')
        if not phone:
            return jsonify({
                "success": False,
                "error": "MISSING_PHONE",
                "message": "請在 Header 中提供 X-User-Phone"
            }), 401
        
        try:
            service = get_service()
            user = service.get_user_by_phone(phone)
            
            if not user:
                return jsonify({
                    "success": False,
                    "error": "USER_NOT_FOUND",
                    "message": "用戶不存在，請先驗證"
                }), 401
            
            if not user.verified:
                return jsonify({
                    "success": False,
                    "error": "NOT_VERIFIED",
                    "message": "請先完成 WhatsApp 驗證"
                }), 401
            
            # 將用戶信息存儲到請求上下文
            request.whatsapp_user = user
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return jsonify({
                "success": False,
                "error": "AUTH_ERROR",
                "message": str(e)
            }), 500
    
    return decorated_function


# ============ API 端點 ============

@whatsapp_bp.route('/health', methods=['GET'])
def health_check():
    """
    WhatsApp 服務健康檢查
    
    Response:
    {
        "status": "ok",
        "available": true,
        "provider": "mock"
    }
    """
    if not WHATSAPP_AVAILABLE:
        return jsonify({
            "status": "unavailable",
            "available": False,
            "message": "WhatsApp module not loaded"
        }), 503
    
    try:
        service = get_service()
        stats = service.get_stats()
        
        return jsonify({
            "status": "ok",
            "available": True,
            "provider": stats.get("provider", "unknown"),
            "stats": {
                "total_users": stats.get("total_users", 0),
                "verified_users": stats.get("verified_users", 0)
            }
        })
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({
            "status": "error",
            "available": False,
            "message": str(e)
        }), 500


@whatsapp_bp.route('/verify', methods=['POST'])
def send_verification():
    """
    發送 WhatsApp 驗證碼
    
    Request Body:
    {
        "phone": "+85291234567"  // 支持各種格式
    }
    
    Response:
    {
        "success": true,
        "message": "驗證碼已發送到您的 WhatsApp",
        "phone": "+85291234567",
        "expires_in": 600
    }
    """
    if not WHATSAPP_AVAILABLE:
        return jsonify({
            "success": False,
            "error": "NOT_AVAILABLE",
            "message": "WhatsApp 服務暫不可用"
        }), 503
    
    try:
        data = request.get_json()
        if not data or 'phone' not in data:
            return jsonify({
                "success": False,
                "error": "MISSING_PHONE",
                "message": "請提供手機號碼"
            }), 400
        
        phone = data['phone'].strip()
        if not phone:
            return jsonify({
                "success": False,
                "error": "EMPTY_PHONE",
                "message": "手機號碼不能為空"
            }), 400
        
        service = get_service()
        result = service.send_verification_code(phone)
        
        status_code = 200 if result.get('success') else 500
        return jsonify(result), status_code
        
    except Exception as e:
        logger.error(f"Send verification error: {e}")
        return jsonify({
            "success": False,
            "error": "INTERNAL_ERROR",
            "message": str(e)
        }), 500


@whatsapp_bp.route('/verify/code', methods=['POST'])
def verify_code():
    """
    驗證用戶輸入的驗證碼
    
    Request Body:
    {
        "phone": "+85291234567",
        "code": "123456"
    }
    
    Response:
    {
        "success": true,
        "message": "驗證成功",
        "user": {
            "id": 1,
            "phone": "+85291234567",
            "verified": true
        }
    }
    """
    if not WHATSAPP_AVAILABLE:
        return jsonify({
            "success": False,
            "error": "NOT_AVAILABLE",
            "message": "WhatsApp 服務暫不可用"
        }), 503
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "MISSING_DATA",
                "message": "請提供請求數據"
            }), 400
        
        phone = data.get('phone', '').strip()
        code = data.get('code', '').strip()
        
        if not phone:
            return jsonify({
                "success": False,
                "error": "MISSING_PHONE",
                "message": "請提供手機號碼"
            }), 400
        
        if not code:
            return jsonify({
                "success": False,
                "error": "MISSING_CODE",
                "message": "請提供驗證碼"
            }), 400
        
        # 驗證碼格式檢查
        if not code.isdigit() or len(code) != 6:
            return jsonify({
                "success": False,
                "error": "INVALID_CODE_FORMAT",
                "message": "驗證碼必須是 6 位數字"
            }), 400
        
        service = get_service()
        result = service.verify_code(phone, code)
        
        status_code = 200 if result.get('success') else 400
        return jsonify(result), status_code
        
    except Exception as e:
        logger.error(f"Verify code error: {e}")
        return jsonify({
            "success": False,
            "error": "INTERNAL_ERROR",
            "message": str(e)
        }), 500


@whatsapp_bp.route('/user/profile', methods=['GET'])
@require_verified_user
def get_user_profile():
    """
    獲取當前用戶資料
    
    Header:
        X-User-Phone: +85291234567
    
    Response:
    {
        "success": true,
        "user": {
            "id": 1,
            "phone": "+85291234567",
            "name": "張三",
            "company": "ABC Trading",
            "verified": true,
            "created_at": "2026-03-15T10:00:00"
        }
    }
    """
    user = request.whatsapp_user
    return jsonify({
        "success": True,
        "user": user.to_dict()
    })


@whatsapp_bp.route('/user/profile', methods=['PUT'])
@require_verified_user
def update_user_profile():
    """
    更新用戶資料
    
    Header:
        X-User-Phone: +85291234567
    
    Request Body:
    {
        "name": "張三",
        "company": "ABC Trading Ltd"
    }
    
    Response:
    {
        "success": true,
        "message": "資料更新成功"
    }
    """
    try:
        data = request.get_json() or {}
        user = request.whatsapp_user
        
        service = get_service()
        success = service.update_user_profile(
            user.phone,
            name=data.get('name'),
            company=data.get('company')
        )
        
        if success:
            return jsonify({
                "success": True,
                "message": "資料更新成功"
            })
        else:
            return jsonify({
                "success": False,
                "error": "UPDATE_FAILED",
                "message": "資料更新失敗"
            }), 500
            
    except Exception as e:
        logger.error(f"Update profile error: {e}")
        return jsonify({
            "success": False,
            "error": "INTERNAL_ERROR",
            "message": str(e)
        }), 500


@whatsapp_bp.route('/share', methods=['POST'])
@require_verified_user
def share_file():
    """
    分享翻譯文件到 WhatsApp
    
    Header:
        X-User-Phone: +85291234567
    
    Request Body:
    {
        "file_name": "contract.docx",
        "file_type": "docx",
        "file_size": 10240,
        "share_type": "self",  // self, customer, link
        "target_phone": "+8613800138000",  // share_type=customer 時需要
        "target_name": "李四",  // 可選
        "share_link": "https://example.com/download/xxx"  // share_type=link 時需要
    }
    
    Response:
    {
        "success": true,
        "message": "文件分享成功",
        "share_id": 1,
        "sent_to": "+85291234567",
        "share_link": "https://example.com/download/xxx"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "MISSING_DATA",
                "message": "請提供請求數據"
            }), 400
        
        # 驗證必填字段
        required_fields = ['file_name', 'file_type', 'file_size']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "success": False,
                    "error": f"MISSING_{field.upper()}",
                    "message": f"請提供 {field}"
                }), 400
        
        share_type = data.get('share_type', 'self')
        if share_type not in ['self', 'customer', 'link']:
            return jsonify({
                "success": False,
                "error": "INVALID_SHARE_TYPE",
                "message": "share_type 必須是 self、customer 或 link"
            }), 400
        
        # customer 類型需要 target_phone
        if share_type == 'customer' and not data.get('target_phone'):
            return jsonify({
                "success": False,
                "error": "MISSING_TARGET_PHONE",
                "message": "分享給客戶時需要提供 target_phone"
            }), 400
        
        user = request.whatsapp_user
        service = get_service()
        
        file_info = {
            'name': data['file_name'],
            'type': data['file_type'],
            'size': data['file_size']
        }
        
        result = service.share_file(
            user_phone=user.phone,
            file_info=file_info,
            share_type=share_type,
            target_phone=data.get('target_phone'),
            target_name=data.get('target_name'),
            share_link=data.get('share_link')
        )
        
        status_code = 200 if result.get('success') else 500
        return jsonify(result), status_code
        
    except Exception as e:
        logger.error(f"Share file error: {e}")
        return jsonify({
            "success": False,
            "error": "INTERNAL_ERROR",
            "message": str(e)
        }), 500


@whatsapp_bp.route('/share/history', methods=['GET'])
@require_verified_user
def get_share_history():
    """
    獲取分享歷史
    
    Header:
        X-User-Phone: +85291234567
    
    Query Parameters:
        limit: 返回數量限制（默認 50）
        client_phone: 篩選特定客戶的分享記錄
    
    Response:
    {
        "success": true,
        "history": [
            {
                "id": 1,
                "file_name": "contract.docx",
                "file_type": "docx",
                "file_size": 10240,
                "target_phone": "+8613800138000",
                "target_name": "李四",
                "share_type": "customer",
                "share_link": "https://...",
                "message_sent": true,
                "created_at": "2026-03-15T10:00:00"
            }
        ]
    }
    """
    try:
        user = request.whatsapp_user
        service = get_service()
        
        limit = request.args.get('limit', 50, type=int)
        client_phone = request.args.get('client_phone')
        
        if client_phone:
            history = service.get_client_history(user.phone, client_phone)
        else:
            history = service.get_share_history(user.phone, limit)
        
        return jsonify({
            "success": True,
            "history": history,
            "count": len(history)
        })
        
    except Exception as e:
        logger.error(f"Get history error: {e}")
        return jsonify({
            "success": False,
            "error": "INTERNAL_ERROR",
            "message": str(e)
        }), 500


# ============ 客戶通訊錄 API ============

@whatsapp_bp.route('/contacts', methods=['GET'])
@require_verified_user
def get_contacts():
    """
    獲取客戶通訊錄
    
    Header:
        X-User-Phone: +85291234567
    
    Response:
    {
        "success": true,
        "contacts": [
            {
                "id": 1,
                "name": "李四",
                "phone": "+8613800138000",
                "company": "XYZ Import",
                "notes": "重要客戶",
                "created_at": "2026-03-15T10:00:00"
            }
        ]
    }
    """
    try:
        user = request.whatsapp_user
        service = get_service()
        
        contacts = service.get_contacts(user.phone)
        
        return jsonify({
            "success": True,
            "contacts": contacts,
            "count": len(contacts)
        })
        
    except Exception as e:
        logger.error(f"Get contacts error: {e}")
        return jsonify({
            "success": False,
            "error": "INTERNAL_ERROR",
            "message": str(e)
        }), 500


@whatsapp_bp.route('/contacts', methods=['POST'])
@require_verified_user
def add_contact():
    """
    添加客戶到通訊錄
    
    Header:
        X-User-Phone: +85291234567
    
    Request Body:
    {
        "name": "李四",
        "phone": "+8613800138000",
        "company": "XYZ Import",  // 可選
        "notes": "重要客戶"  // 可選
    }
    
    Response:
    {
        "success": true,
        "contact_id": 1,
        "message": "客戶添加成功"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "MISSING_DATA",
                "message": "請提供請求數據"
            }), 400
        
        # 驗證必填字段
        if not data.get('name'):
            return jsonify({
                "success": False,
                "error": "MISSING_NAME",
                "message": "請提供客戶名稱"
            }), 400
        
        if not data.get('phone'):
            return jsonify({
                "success": False,
                "error": "MISSING_PHONE",
                "message": "請提供客戶手機號碼"
            }), 400
        
        user = request.whatsapp_user
        service = get_service()
        
        result = service.add_contact(
            user_phone=user.phone,
            name=data['name'],
            contact_phone=data['phone'],
            company=data.get('company'),
            notes=data.get('notes')
        )
        
        status_code = 200 if result.get('success') else 400
        return jsonify(result), status_code
        
    except Exception as e:
        logger.error(f"Add contact error: {e}")
        return jsonify({
            "success": False,
            "error": "INTERNAL_ERROR",
            "message": str(e)
        }), 500


@whatsapp_bp.route('/stats', methods=['GET'])
@require_verified_user
def get_stats():
    """
    獲取 WhatsApp 整合統計
    
    Header:
        X-User-Phone: +85291234567
    
    Response:
    {
        "success": true,
        "stats": {
            "provider": "mock",
            "total_users": 10,
            "verified_users": 8,
            "user_stats": {
                "total_shares": 5,
                "contacts": 3
            }
        }
    }
    """
    try:
        user = request.whatsapp_user
        service = get_service()
        
        stats = service.get_stats(user.phone)
        
        return jsonify({
            "success": True,
            "stats": stats
        })
        
    except Exception as e:
        logger.error(f"Get stats error: {e}")
        return jsonify({
            "success": False,
            "error": "INTERNAL_ERROR",
            "message": str(e)
        }), 500


# ============ 初始化函數 ============

def init_whatsapp_routes(app):
    """
    初始化 WhatsApp 路由
    在主應用中調用此函數註冊 Blueprint
    
    Args:
        app: Flask 應用實例
    """
    app.register_blueprint(whatsapp_bp)
    logger.info("WhatsApp routes registered")
    
    # 初始化服務（確保數據庫表已創建）
    if WHATSAPP_AVAILABLE:
        try:
            get_whatsapp_service()
            logger.info("WhatsApp service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize WhatsApp service: {e}")
