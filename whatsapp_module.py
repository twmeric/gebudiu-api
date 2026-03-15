#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WhatsApp 整合模組 - GeBuDiu 翻譯服務
為外貿人員提供 WhatsApp 驗證和文件分享功能

參考 Openbox 項目的 Cloudwapi 實現
支持 WhatsApp Business API
"""

import os
import re
import json
import logging
import sqlite3
import hashlib
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

import requests
from flask import current_app

logger = logging.getLogger(__name__)

# ============ 配置常量 ============

class WhatsAppProvider(Enum):
    """WhatsApp 服務提供商"""
    CLOUDWAPI = "cloudwapi"
    META = "meta"
    MOCK = "mock"  # 用於測試

# Cloudwapi 端點
CLOUDWAPI_MESSAGE_ENDPOINT = 'https://unofficial.cloudwapi.in/send-message'
CLOUDWAPI_MEDIA_ENDPOINT = 'https://unofficial.cloudwapi.in/send-media'

# 驗證碼配置
VERIFICATION_CODE_LENGTH = 6
VERIFICATION_CODE_EXPIRY_MINUTES = 10


@dataclass
class WhatsAppUser:
    """WhatsApp 用戶資料"""
    id: int
    phone: str  # 國際格式: +852XXXXXXXX
    name: Optional[str]
    company: Optional[str]
    verified: bool
    verification_code: Optional[str]
    code_expires_at: Optional[str]
    created_at: str
    last_login_at: Optional[str]
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "phone": self.phone,
            "name": self.name,
            "company": self.company,
            "verified": self.verified,
            "created_at": self.created_at,
            "last_login_at": self.last_login_at
        }


@dataclass
class ShareRecord:
    """文件分享記錄"""
    id: int
    user_id: int
    file_name: str
    file_type: str  # docx, xlsx
    file_size: int
    target_phone: Optional[str]  # 發送給的客戶號碼
    target_name: Optional[str]   # 客戶名稱
    share_type: str  # self, customer, link
    share_link: Optional[str]
    message_sent: bool
    created_at: str
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "file_name": self.file_name,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "target_phone": self.target_phone,
            "target_name": self.target_name,
            "share_type": self.share_type,
            "share_link": self.share_link,
            "message_sent": self.message_sent,
            "created_at": self.created_at
        }


class WhatsAppService:
    """
    WhatsApp 服務核心類
    處理驗證、消息發送、分享記錄
    """
    
    def __init__(self, db_path: str = None):
        """
        初始化 WhatsApp 服務
        
        Args:
            db_path: SQLite 數據庫路徑，默認使用 /data/whatsapp.db
        """
        if db_path is None:
            db_path = os.getenv("WHATSAPP_DB_PATH", "/data/whatsapp.db")
        
        self.db_path = db_path
        self.provider = self._get_provider()
        
        # 確保目錄存在
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, exist_ok=True)
            except Exception as e:
                logger.warning(f"Failed to create db directory {db_dir}: {e}")
                self.db_path = "whatsapp.db"
        
        self._init_db()
        logger.info(f"WhatsAppService initialized: {self.db_path}, provider={self.provider.value}")
    
    def _get_provider(self) -> WhatsAppProvider:
        """獲取配置的 WhatsApp 提供商"""
        provider_str = os.getenv("WHATSAPP_PROVIDER", "mock").lower()
        try:
            return WhatsAppProvider(provider_str)
        except ValueError:
            logger.warning(f"Unknown provider {provider_str}, using mock")
            return WhatsAppProvider.MOCK
    
    def _init_db(self):
        """初始化數據庫表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 用戶表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS whatsapp_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT UNIQUE NOT NULL,
                name TEXT,
                company TEXT,
                verified BOOLEAN DEFAULT 0,
                verification_code TEXT,
                code_expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login_at TIMESTAMP
            )
        """)
        
        # 分享記錄表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS whatsapp_shares (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                file_name TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                target_phone TEXT,
                target_name TEXT,
                share_type TEXT NOT NULL,  -- self, customer, link
                share_link TEXT,
                message_sent BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES whatsapp_users(id)
            )
        """)
        
        # 客戶通訊錄表（方便用戶管理常用客戶）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS whatsapp_contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                company TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES whatsapp_users(id),
                UNIQUE(user_id, phone)
            )
        """)
        
        # 創建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_whatsapp_users_phone 
            ON whatsapp_users(phone)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_whatsapp_shares_user 
            ON whatsapp_shares(user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_whatsapp_contacts_user 
            ON whatsapp_contacts(user_id)
        """)
        
        conn.commit()
        conn.close()
        logger.info("WhatsApp database tables initialized")
    
    # ============ 驗證相關方法 ============
    
    def _normalize_phone(self, phone: str) -> str:
        """
        標準化手機號碼為國際格式
        
        Args:
            phone: 輸入的手機號碼（各種格式）
            
        Returns:
            標準化格式: +區碼號碼 (如 +85291234567)
        """
        # 移除所有非數字字符
        digits = re.sub(r'\D', '', phone)
        
        # 如果開頭是 00，替換為 +
        if digits.startswith('00'):
            digits = '+' + digits[2:]
        # 如果沒有 + 開頭，根據長度判斷
        elif not digits.startswith('+'):
            # 中國大陸號碼 (11位)
            if len(digits) == 11 and digits.startswith('1'):
                digits = '+86' + digits
            # 香港號碼 (8位)
            elif len(digits) == 8:
                digits = '+852' + digits
            # 其他情況，假設已經包含區碼
            else:
                digits = '+' + digits
        
        return digits
    
    def _generate_verification_code(self) -> str:
        """生成隨機驗證碼"""
        return ''.join(secrets.choice(string.digits) for _ in range(VERIFICATION_CODE_LENGTH))
    
    def send_verification_code(self, phone: str) -> Dict:
        """
        發送 WhatsApp 驗證碼
        
        Args:
            phone: 用戶手機號碼
            
        Returns:
            操作結果字典
        """
        normalized_phone = self._normalize_phone(phone)
        code = self._generate_verification_code()
        expires_at = datetime.now() + timedelta(minutes=VERIFICATION_CODE_EXPIRY_MINUTES)
        
        # 保存到數據庫
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 檢查用戶是否存在
        cursor.execute("SELECT id FROM whatsapp_users WHERE phone = ?", (normalized_phone,))
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute("""
                UPDATE whatsapp_users 
                SET verification_code = ?, code_expires_at = ?
                WHERE phone = ?
            """, (code, expires_at.isoformat(), normalized_phone))
        else:
            cursor.execute("""
                INSERT INTO whatsapp_users (phone, verification_code, code_expires_at, verified)
                VALUES (?, ?, ?, 0)
            """, (normalized_phone, code, expires_at.isoformat()))
        
        conn.commit()
        conn.close()
        
        # 發送 WhatsApp 消息
        message = f"""🌐 GeBuDiu 翻譯服務

您的驗證碼是：*{code}*

此驗證碼 {VERIFICATION_CODE_EXPIRY_MINUTES} 分鐘內有效。

如非本人操作，請忽略此消息。"""
        
        result = self._send_whatsapp_message(normalized_phone, message)
        
        if result.get('success'):
            logger.info(f"Verification code sent to {normalized_phone}")
            return {
                "success": True,
                "message": "驗證碼已發送到您的 WhatsApp",
                "phone": normalized_phone,
                "expires_in": VERIFICATION_CODE_EXPIRY_MINUTES * 60  # 秒
            }
        else:
            logger.error(f"Failed to send verification code: {result.get('error')}")
            return {
                "success": False,
                "error": result.get('error', 'Failed to send message'),
                "message": "發送失敗，請檢查手機號碼是否正確"
            }
    
    def verify_code(self, phone: str, code: str) -> Dict:
        """
        驗證用戶輸入的驗證碼
        
        Args:
            phone: 用戶手機號碼
            code: 用戶輸入的驗證碼
            
        Returns:
            驗證結果字典
        """
        normalized_phone = self._normalize_phone(phone)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, verification_code, code_expires_at, name, company
            FROM whatsapp_users 
            WHERE phone = ?
        """, (normalized_phone,))
        
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return {
                "success": False,
                "error": "USER_NOT_FOUND",
                "message": "請先獲取驗證碼"
            }
        
        user_id, stored_code, expires_at, name, company = row
        
        # 檢查驗證碼是否過期
        if expires_at and datetime.fromisoformat(expires_at) < datetime.now():
            conn.close()
            return {
                "success": False,
                "error": "CODE_EXPIRED",
                "message": "驗證碼已過期，請重新獲取"
            }
        
        # 檢查驗證碼是否匹配
        if stored_code != code:
            conn.close()
            return {
                "success": False,
                "error": "INVALID_CODE",
                "message": "驗證碼錯誤，請重新輸入"
            }
        
        # 驗證成功，更新用戶狀態
        now = datetime.now().isoformat()
        cursor.execute("""
            UPDATE whatsapp_users 
            SET verified = 1, verification_code = NULL, 
                code_expires_at = NULL, last_login_at = ?
            WHERE id = ?
        """, (now, user_id))
        
        conn.commit()
        conn.close()
        
        # 發送歡迎消息
        welcome_message = f"""✅ 驗證成功！

歡迎使用 GeBuDiu 專業翻譯服務。

📄 您可以：
• 上傳 DOCX/XLSX 文件進行翻譯
• 翻譯完成後直接分享到 WhatsApp
• 管理客戶通訊錄

🌐 訪問：{os.getenv('FRONTEND_URL', 'https://gebudiu.io')}"""
        
        self._send_whatsapp_message(normalized_phone, welcome_message)
        
        logger.info(f"User {normalized_phone} verified successfully")
        
        return {
            "success": True,
            "message": "驗證成功",
            "user": {
                "id": user_id,
                "phone": normalized_phone,
                "name": name,
                "company": company,
                "verified": True
            }
        }
    
    def get_user_by_phone(self, phone: str) -> Optional[WhatsAppUser]:
        """根據手機號獲取用戶"""
        normalized_phone = self._normalize_phone(phone)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, phone, name, company, verified, verification_code,
                   code_expires_at, created_at, last_login_at
            FROM whatsapp_users 
            WHERE phone = ?
        """, (normalized_phone,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return WhatsAppUser(*row)
        return None
    
    def update_user_profile(self, phone: str, name: str = None, company: str = None) -> bool:
        """更新用戶資料"""
        normalized_phone = self._normalize_phone(phone)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        updates = []
        params = []
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if company is not None:
            updates.append("company = ?")
            params.append(company)
        
        if not updates:
            conn.close()
            return False
        
        params.append(normalized_phone)
        cursor.execute(f"""
            UPDATE whatsapp_users 
            SET {', '.join(updates)}
            WHERE phone = ?
        """, params)
        
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        
        return success
    
    # ============ 分享相關方法 ============
    
    def share_file(self, user_phone: str, file_info: Dict, 
                   share_type: str = "self", target_phone: str = None,
                   target_name: str = None, share_link: str = None) -> Dict:
        """
        記錄文件分享並發送 WhatsApp 消息
        
        Args:
            user_phone: 當前用戶手機號
            file_info: 文件信息字典
            share_type: 分享類型 (self/customer/link)
            target_phone: 目標客戶手機號
            target_name: 目標客戶名稱
            share_link: 分享鏈接
            
        Returns:
            操作結果字典
        """
        user = self.get_user_by_phone(user_phone)
        if not user or not user.verified:
            return {
                "success": False,
                "error": "NOT_VERIFIED",
                "message": "請先完成 WhatsApp 驗證"
            }
        
        # 標準化目標手機號
        normalized_target = None
        if target_phone:
            normalized_target = self._normalize_phone(target_phone)
        
        # 保存分享記錄
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO whatsapp_shares 
            (user_id, file_name, file_type, file_size, target_phone, 
             target_name, share_type, share_link, message_sent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
        """, (user.id, file_info.get('name'), file_info.get('type'),
              file_info.get('size'), normalized_target, target_name,
              share_type, share_link))
        
        share_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # 構建消息
        message = self._build_share_message(file_info, share_type, target_name, share_link)
        
        # 確定發送目標
        send_to = user.phone  # 默認發給自己
        if share_type == "customer" and normalized_target:
            send_to = normalized_target
        
        # 發送 WhatsApp 消息
        result = self._send_whatsapp_message(send_to, message)
        
        if result.get('success'):
            # 更新發送狀態
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE whatsapp_shares SET message_sent = 1 WHERE id = ?
            """, (share_id,))
            conn.commit()
            conn.close()
            
            logger.info(f"File shared: {file_info.get('name')} to {send_to}")
            
            return {
                "success": True,
                "message": "文件分享成功",
                "share_id": share_id,
                "sent_to": send_to,
                "share_link": share_link
            }
        else:
            logger.error(f"Failed to share file: {result.get('error')}")
            return {
                "success": False,
                "error": result.get('error', 'Failed to send message'),
                "share_id": share_id,
                "message": "分享記錄已保存，但消息發送失敗"
            }
    
    def _build_share_message(self, file_info: Dict, share_type: str, 
                            target_name: str = None, share_link: str = None) -> str:
        """構建分享消息內容"""
        file_name = file_info.get('name', '未知文件')
        file_type = file_info.get('type', 'document').upper()
        
        # 文件大小格式化
        size = file_info.get('size', 0)
        if size < 1024:
            size_str = f"{size} B"
        elif size < 1024 * 1024:
            size_str = f"{size / 1024:.1f} KB"
        else:
            size_str = f"{size / (1024 * 1024):.1f} MB"
        
        company = os.getenv('COMPANY_NAME', 'GeBuDiu 翻譯服務')
        
        if share_type == "self":
            message = f"""📄 翻譯完成！

文件名：{file_name}
格式：{file_type}
大小：{size_str}

🌐 由 {company} 提供專業翻譯"""
        elif share_type == "customer":
            greeting = f"您好 {target_name}，" if target_name else "您好，"
            message = f"""{greeting}

📄 為您準備了翻譯文件：

文件名：{file_name}
格式：{file_type}
大小：{size_str}

{f'📎 下載鏈接：{share_link}' if share_link else ''}

🌐 由 {company} 提供專業翻譯
如有任何問題，請隨時聯繫。"""
        else:  # link
            message = f"""📄 翻譯文件分享

文件名：{file_name}
格式：{file_type}
大小：{size_str}

📎 下載鏈接：{share_link}

🌐 由 {company} 提供專業翻譯"""
        
        return message
    
    def get_share_history(self, user_phone: str, limit: int = 50) -> List[Dict]:
        """
        獲取用戶的分享歷史
        
        Args:
            user_phone: 用戶手機號
            limit: 返回記錄數量限制
            
        Returns:
            分享記錄列表
        """
        user = self.get_user_by_phone(user_phone)
        if not user:
            return []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, file_name, file_type, file_size, target_phone,
                   target_name, share_type, share_link, message_sent, created_at
            FROM whatsapp_shares 
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user.id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        records = []
        for row in rows:
            record = ShareRecord(*row)
            records.append(record.to_dict())
        
        return records
    
    def get_client_history(self, user_phone: str, client_phone: str) -> List[Dict]:
        """
        獲取發送給特定客戶的文件歷史
        
        Args:
            user_phone: 當前用戶手機號
            client_phone: 客戶手機號
            
        Returns:
            分享記錄列表
        """
        user = self.get_user_by_phone(user_phone)
        if not user:
            return []
        
        normalized_client = self._normalize_phone(client_phone)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, file_name, file_type, file_size, target_phone,
                   target_name, share_type, share_link, message_sent, created_at
            FROM whatsapp_shares 
            WHERE user_id = ? AND target_phone = ?
            ORDER BY created_at DESC
        """, (user.id, normalized_client))
        
        rows = cursor.fetchall()
        conn.close()
        
        records = []
        for row in rows:
            record = ShareRecord(*row)
            records.append(record.to_dict())
        
        return records
    
    # ============ 客戶通訊錄管理 ============
    
    def add_contact(self, user_phone: str, name: str, contact_phone: str, 
                    company: str = None, notes: str = None) -> Dict:
        """添加客戶到通訊錄"""
        user = self.get_user_by_phone(user_phone)
        if not user:
            return {"success": False, "error": "USER_NOT_FOUND"}
        
        normalized_phone = self._normalize_phone(contact_phone)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO whatsapp_contacts (user_id, name, phone, company, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (user.id, name, normalized_phone, company, notes))
            conn.commit()
            contact_id = cursor.lastrowid
            conn.close()
            
            return {
                "success": True,
                "contact_id": contact_id,
                "message": "客戶添加成功"
            }
        except sqlite3.IntegrityError:
            conn.close()
            return {
                "success": False,
                "error": "DUPLICATE_CONTACT",
                "message": "該客戶手機號已存在"
            }
    
    def get_contacts(self, user_phone: str) -> List[Dict]:
        """獲取用戶的客戶通訊錄"""
        user = self.get_user_by_phone(user_phone)
        if not user:
            return []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, phone, company, notes, created_at
            FROM whatsapp_contacts 
            WHERE user_id = ?
            ORDER BY name
        """, (user.id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        contacts = []
        for row in rows:
            contacts.append({
                "id": row[0],
                "name": row[1],
                "phone": row[2],
                "company": row[3],
                "notes": row[4],
                "created_at": row[5]
            })
        
        return contacts
    
    # ============ WhatsApp 發送實現 ============
    
    def _send_whatsapp_message(self, to: str, message: str) -> Dict:
        """
        發送 WhatsApp 消息
        根據配置的提供商選擇發送方式
        
        Args:
            to: 接收方手機號（國際格式）
            message: 消息內容
            
        Returns:
            發送結果字典
        """
        if self.provider == WhatsAppProvider.MOCK:
            return self._mock_send(to, message)
        elif self.provider == WhatsAppProvider.CLOUDWAPI:
            return self._send_cloudwapi(to, message)
        elif self.provider == WhatsAppProvider.META:
            return self._send_meta(to, message)
        else:
            return {"success": False, "error": "Unknown provider"}
    
    def _mock_send(self, to: str, message: str) -> Dict:
        """Mock 發送（用於測試）"""
        logger.info(f"[MOCK] WhatsApp to {to}: {message[:100]}...")
        return {
            "success": True,
            "mock": True,
            "message_id": f"mock_{datetime.now().timestamp()}"
        }
    
    def _send_cloudwapi(self, to: str, message: str) -> Dict:
        """使用 Cloudwapi 發送消息"""
        api_key = os.getenv("CLOUDWAPI_API_KEY")
        sender = os.getenv("CLOUDWAPI_SENDER", "85262322466")
        
        if not api_key:
            logger.error("CLOUDWAPI_API_KEY not configured")
            return {"success": False, "error": "API Key not configured"}
        
        try:
            request_body = {
                "api_key": api_key,
                "sender": re.sub(r'\D', '', sender),
                "number": re.sub(r'\D', '', to),
                "message": message
            }
            
            response = requests.post(
                CLOUDWAPI_MESSAGE_ENDPOINT,
                json=request_body,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            result = response.json()
            
            if result.get("status") == True or result.get("status") == "success":
                return {
                    "success": True,
                    "message_id": result.get("message", {}).get("key", {}).get("id")
                }
            else:
                return {
                    "success": False,
                    "error": result.get("msg") or result.get("message") or "Send failed"
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Cloudwapi request error: {e}")
            return {"success": False, "error": f"Request failed: {str(e)}"}
        except Exception as e:
            logger.error(f"Cloudwapi error: {e}")
            return {"success": False, "error": str(e)}
    
    def _send_meta(self, to: str, message: str) -> Dict:
        """使用 Meta WhatsApp Business API 發送（預留）"""
        # TODO: 實現 Meta API 發送
        logger.warning("Meta API not implemented yet")
        return {"success": False, "error": "Meta API not implemented"}
    
    # ============ 統計和報告 ============
    
    def get_stats(self, user_phone: str = None) -> Dict:
        """
        獲取 WhatsApp 整合統計
        
        Args:
            user_phone: 特定用戶的手機號（可選）
            
        Returns:
            統計數據字典
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {
            "provider": self.provider.value,
            "total_users": 0,
            "verified_users": 0,
            "total_shares": 0,
            "successful_shares": 0
        }
        
        # 用戶統計
        cursor.execute("""
            SELECT COUNT(*), SUM(CASE WHEN verified = 1 THEN 1 ELSE 0 END)
            FROM whatsapp_users
        """)
        total, verified = cursor.fetchone()
        stats["total_users"] = total or 0
        stats["verified_users"] = verified or 0
        
        # 分享統計
        cursor.execute("""
            SELECT COUNT(*), SUM(CASE WHEN message_sent = 1 THEN 1 ELSE 0 END)
            FROM whatsapp_shares
        """)
        total_shares, successful = cursor.fetchone()
        stats["total_shares"] = total_shares or 0
        stats["successful_shares"] = successful or 0
        
        # 如果用戶指定，添加用戶特定統計
        if user_phone:
            user = self.get_user_by_phone(user_phone)
            if user:
                cursor.execute("""
                    SELECT COUNT(*) FROM whatsapp_shares WHERE user_id = ?
                """, (user.id,))
                user_shares = cursor.fetchone()[0] or 0
                
                cursor.execute("""
                    SELECT COUNT(*) FROM whatsapp_contacts WHERE user_id = ?
                """, (user.id,))
                user_contacts = cursor.fetchone()[0] or 0
                
                stats["user_stats"] = {
                    "total_shares": user_shares,
                    "contacts": user_contacts
                }
        
        conn.close()
        return stats


# ============ 全局實例 ============

_whatsapp_service = None

def get_whatsapp_service(db_path: str = None) -> WhatsAppService:
    """獲取 WhatsApp 服務單例"""
    global _whatsapp_service
    if _whatsapp_service is None:
        _whatsapp_service = WhatsAppService(db_path)
    return _whatsapp_service
