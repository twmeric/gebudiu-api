#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
格不丢翻译 API - 安全加强版
模块化架构，支持7大专业领域
"""

import os
import sys
import hashlib
import json
import time
import logging
import re
from io import BytesIO
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from flask import Flask, request, send_file, jsonify, make_response
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from docx import Document
from openai import OpenAI, APIError, RateLimitError
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('translation.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 创建应用
app = Flask(__name__)

# 安全配置 - 允許所有來源（生產環境需要時再限制）
CORS(app, origins="*", supports_credentials=False)

# 額外 CORS 處理 - 確保所有響應都帶 CORS 頭（包括錯誤響應）
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

# 文件配置
MAX_FILE_SIZE = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = {'.docx', '.xlsx'}

# DeepSeek API 配置 - 延遲加載
def get_deepseek_client():
    """延遲初始化 DeepSeek 客戶端"""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    
    # Debug: 記錄所有環境變量（隱藏敏感值）
    if not api_key:
        logger.error("DEEPSEEK_API_KEY not found!")
        logger.info(f"Available env vars: {[k for k in os.environ.keys() if not k.startswith('_')][:20]}")
        # 嘗試小寫
        api_key = os.getenv("deepseek_api_key") or os.getenv("Deepseek_Api_Key")
        if api_key:
            logger.info("Found API key with different case!")
        else:
            raise ValueError("DEEPSEEK_API_KEY environment variable is required")
    
    logger.info(f"API Key found: {api_key[:10]}... (length: {len(api_key)})")
    return OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")

# 延遲初始化
deepseek_client = None

# 领域配置
DOMAINS = {
    "general": {
        "name": "通用领域",
        "name_en": "General",
        "icon": "📋"
    },
    "electronics": {
        "name": "电子产品",
        "name_en": "Electronics",
        "icon": "🔌"
    },
    "medical": {
        "name": "医疗器械",
        "name_en": "Medical",
        "icon": "🏥"
    },
    "legal": {
        "name": "法律合同",
        "name_en": "Legal",
        "icon": "⚖️"
    },
    "marketing": {
        "name": "市场营销",
        "name_en": "Marketing",
        "icon": "📢"
    },
    "industrial": {
        "name": "工业技术",
        "name_en": "Industrial",
        "icon": "🏭"
    },
    "software": {
        "name": "软件/IT",
        "name_en": "Software",
        "icon": "💻"
    }
}

# Prompt 模板
PROMPTS = {
    "general": "You are a professional translator. Translate the following Chinese text to English for general business use. Provide ONLY the English translation.",
    "electronics": "You are an electronics industry translator. Use standard technical terminology. Preserve model numbers like G-190. Provide ONLY the English translation.",
    "medical": "You are a medical device translator. Use formal, cautious medical terminology suitable for regulatory compliance. Provide ONLY the English translation.",
    "legal": "You are a legal contract translator. Use precise legal terminology and formal contractual language. Provide ONLY the English translation.",
    "marketing": "You are a marketing copy translator. Make the content persuasive and appealing. Provide ONLY the English translation.",
    "industrial": "You are an industrial/technical translator. Use ISO-standard terminology. Provide ONLY the English translation.",
    "software": "You are a software/IT documentation translator. Preserve code snippets and API names. Provide ONLY the English translation."
}

# 缓存管理
class TranslationCache:
    def __init__(self, cache_file=".translation_cache.json", max_size=10000):
        self.cache_file = cache_file
        self.max_size = max_size
        self.cache = {}
        self._load()
    
    def _load(self):
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
                    logger.info(f"Loaded {len(self.cache)} cached translations")
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")
            self.cache = {}
    
    def _save(self):
        try:
            if len(self.cache) > self.max_size:
                items = list(self.cache.items())
                self.cache = dict(items[-self.max_size:])
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    def get_key(self, text, domain):
        return hashlib.md5(f"{domain}:{text}".encode('utf-8')).hexdigest()
    
    def get(self, text, domain):
        key = self.get_key(text, domain)
        return self.cache.get(key)
    
    def set(self, text, domain, translated):
        key = self.get_key(text, domain)
        self.cache[key] = translated
        self._save()

cache = TranslationCache()

def validate_file(file_storage):
    """验证上传文件 - 增强版"""
    if not file_storage or not getattr(file_storage, 'filename', None):
        return False, "No file selected", None
    
    # 安全处理文件名（移除路径、保留基本名称）
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
    
    # 检查ZIP格式 (docx/xlsx都是ZIP)
    # 支持多种 ZIP 格式标识: PK\x03\x04 (标准) 或 PK\x05\x06 (空ZIP)
    header = file_buffer[:4]
    valid_zip_headers = [b'PK\x03\x04', b'PK\x05\x06', b'PK\x07\x08']
    if header not in valid_zip_headers:
        logger.warning(f"Invalid file header: {header.hex()} for file: {filename}")
        return False, f"Invalid file format (header: {header.hex()}). Please upload a valid .docx or .xlsx file", None
    
    return True, None, {
        "filename": filename,
        "extension": ext,
        "size": len(file_buffer),
        "buffer": file_buffer
    }

def should_translate(text):
    """判断文本是否需要翻译"""
    if not text or len(text.strip()) < 2:
        return False
    
    text = text.strip()
    
    if text.isdigit():
        return False
    
    if text.startswith('http://') or text.startswith('https://'):
        return False
    
    if '@' in text and '.' in text.split('@')[-1]:
        return False
    
    if re.match(r'^G-\d+$', text):
        return False
    
    return True

class TranslationService:
    """批量翻译服务 - 內存優化版（針對 Render 512MB）"""
    
    def __init__(self, domain="general"):
        self.domain = domain
        self.prompt = PROMPTS.get(domain, PROMPTS["general"])
        self.stats = {"api_calls": 0, "cache_hits": 0, "tokens_saved": 0}
    
    def translate_batch(self, texts, max_retries=2):
        """
        批量翻译 - 內存優化，減少 tokens 使用
        
        Args:
            texts: list of (id, text) tuples
            max_retries: 最大重試次數
        
        Returns:
            dict: {id: translated_text}
        """
        if not texts:
            return {}
        
        # 1. 先检查缓存
        to_translate = []
        results = {}
        
        for item_id, text in texts:
            if not should_translate(text):
                results[item_id] = text
                continue
            
            cached = cache.get(text, self.domain)
            if cached:
                results[item_id] = cached
                self.stats["cache_hits"] += 1
            else:
                to_translate.append((item_id, text))
        
        if not to_translate:
            return results
        
        # 2. 構建批量翻譯請求（簡化 prompt 減少 tokens）
        batch_text = "\n".join([f"[{i}] {text[:500]}" for i, (_, text) in enumerate(to_translate)])
        
        for attempt in range(max_retries):
            try:
                client = get_deepseek_client()
                logger.info(f"Batch translating {len(to_translate)} texts, attempt {attempt+1}")
                
                # 簡化 prompt 減少 token 使用
                batch_prompt = f"""{self.prompt}

Translate to English (prefix with [number]):
{batch_text}

Format: [0] Translation"""
                
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": batch_prompt}
                    ],
                    temperature=0.3,
                    max_tokens=2000,  # 減少 tokens 限制
                    timeout=60  # 添加超時
                )
                
                # 3. 解析结果
                raw_output = response.choices[0].message.content.strip()
                translations = self._parse_batch_output(raw_output, len(to_translate))
                
                # 4. 保存到缓存和结果
                for i, (item_id, original) in enumerate(to_translate):
                    translated = translations.get(i, original)
                    cache.set(original, self.domain, translated)
                    results[item_id] = translated
                
                self.stats["api_calls"] += 1
                logger.info(f"Batch translated {len(to_translate)} texts")
                return results
                
            except Exception as e:
                logger.error(f"Batch translation attempt {attempt+1} failed: {e}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(2 ** attempt)  # 指數退避
                else:
                    # 所有重試都失敗，返回原文
                    logger.error(f"All retries failed, returning original text")
                    for item_id, text in to_translate:
                        results[item_id] = text
                    return results
        
        return results
    
    def _parse_batch_output(self, output, expected_count):
        """解析批量翻译的输出"""
        results = {}
        # 匹配 [0] ... [1] ... 格式
        pattern = r'\[(\d+)\]\s*(.+?)(?=\[\d+\]|$)'
        matches = re.findall(pattern, output, re.DOTALL)
        
        for idx_str, text in matches:
            idx = int(idx_str)
            if idx < expected_count:
                results[idx] = text.strip()
        
        return results
    
    def translate_text(self, text):
        """兼容旧接口 - 单条翻译"""
        result = self.translate_batch([("single", text)])
        translated = result.get("single", text)
        is_cached = translated != text and self.stats["cache_hits"] > 0
        return translated, is_cached

class DocxProcessor:
    """DOCX 文档处理器 - 內存優化版（針對 Render 免費版）"""
    
    def __init__(self, translator):
        self.translator = translator
        self.stats = {"paragraphs": 0, "tables": 0, "cells": 0}
    
    def process(self, file_buffer):
        """處理 DOCX 文件 - 流式處理減少內存使用"""
        import gc  # 垃圾回收
        
        doc = Document(BytesIO(file_buffer))
        
        # 1. 收集所有需要翻譯的段落（帶 ID）
        items_to_translate = []
        item_map = {}  # id -> (paragraph, original_text)
        
        def add_item(para, source_type):
            text = para.text.strip()
            if not text or not should_translate(text):
                return
            item_id = f"{source_type}_{len(items_to_translate)}"
            items_to_translate.append((item_id, text))
            item_map[item_id] = para
            self.stats["paragraphs" if source_type == "para" else "cells"] += 1
        
        # 收集正文段落
        for para in doc.paragraphs:
            add_item(para, "para")
        
        # 收集表格段落
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for para in cell.paragraphs:
                        add_item(para, "cell")
            self.stats["tables"] += 1
        
        # 收集頁眉頁腳
        for section in doc.sections:
            for header in [section.header, section.first_page_header]:
                if header:
                    for para in header.paragraphs:
                        add_item(para, "header")
            for footer in [section.footer, section.first_page_footer]:
                if footer:
                    for para in footer.paragraphs:
                        add_item(para, "footer")
        
        logger.info(f"Collected {len(items_to_translate)} items to translate")
        
        # 2. 智能分塊（每批約 2000 tokens，減少內存使用）
        batches = self._create_batches(items_to_translate, max_tokens=2000)
        logger.info(f"Split into {len(batches)} batches")
        
        # 3. 串行處理（避免並行導致的內存峰值）
        # Render 免費版只有 512MB，並行會導致 OOM
        all_results = {}
        
        for batch_idx, batch in enumerate(batches):
            try:
                logger.info(f"Processing batch {batch_idx+1}/{len(batches)} ({len(batch)} items)")
                results = self.translator.translate_batch(batch)
                all_results.update(results)
                
                # 立即回填該批次結果，減少內存佔用
                for item_id, translated in results.items():
                    if item_id in item_map:
                        para = item_map[item_id]
                        original = para.text.strip()
                        if translated != original:
                            self._apply_translation(para, translated)
                        # 清理已處理的引用
                        del item_map[item_id]
                
                # 強制垃圾回收
                gc.collect()
                
            except Exception as e:
                logger.error(f"Batch {batch_idx+1} failed: {e}")
                # 失敗時保留原文
                for item_id, _ in batch:
                    if item_id in item_map:
                        del item_map[item_id]
        
        # 4. 保存結果
        output = BytesIO()
        doc.save(output)
        output.seek(0)
        
        # 清理內存
        gc.collect()
        
        return output
    
    def _create_batches(self, items, max_tokens=2000):
        """智能分塊 - 基於 token 估算（Render 免費版優化：更小的批次）"""
        batches = []
        current_batch = []
        current_tokens = 0
        
        # System prompt + 輸出預留（減少以節省內存）
        overhead = 300  # 減少 system prompt 開銷
        max_items_per_batch = 15  # 限制每批最大項目數
        
        for item_id, text in items:
            # 限制單個文本長度，避免內存溢出
            text = text[:1000] if len(text) > 1000 else text
            
            # 估算：中文字符約 1.5 tokens，加上標記開銷
            est_tokens = len(text) * 1.5 + 10  # +10 for [n] marker
            
            # 檢查是否需要新批次（token 限制或項目數限制）
            should_new_batch = (
                current_tokens + est_tokens + overhead > max_tokens or 
                len(current_batch) >= max_items_per_batch
            ) and current_batch
            
            if should_new_batch:
                batches.append(current_batch)
                current_batch = []
                current_tokens = 0
            
            current_batch.append((item_id, text))
            current_tokens += est_tokens
        
        if current_batch:
            batches.append(current_batch)
        
        logger.info(f"Created {len(batches)} batches with max {max_items_per_batch} items each")
        return batches
    
    def _apply_translation(self, para, translated):
        """應用翻譯結果到段落"""
        if not para.runs:
            return
        
        # 保留第一個 run 的格式，替換文本
        para.runs[0].text = translated
        # 清空其他 runs
        for run in para.runs[1:]:
            run.text = ""

class XlsxProcessor:
    """XLSX 处理器"""
    
    def __init__(self, translator):
        self.translator = translator
        self.stats = {"cells": 0}
    
    def process(self, file_buffer):
        from openpyxl import load_workbook
        
        wb = load_workbook(BytesIO(file_buffer))
        
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            for row in ws.iter_rows():
                for cell in row:
                    if cell.value and isinstance(cell.value, str):
                        if should_translate(cell.value):
                            translated, _ = self.translator.translate_text(cell.value)
                            cell.value = translated
                            self.stats["cells"] += 1
        
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return output

# API 路由
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "service": "格不丢翻译 API",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/domains', methods=['GET'])
def get_domains():
    return jsonify({
        "domains": {
            k: {"name": v["name"], "name_en": v["name_en"], "icon": v["icon"]}
            for k, v in DOMAINS.items()
        }
    })

@app.route('/translate', methods=['POST'])
@limiter.limit("10 per minute")
def translate():
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
        
        translator = TranslationService(domain)
        
        if file_info["extension"] == '.docx':
            processor = DocxProcessor(translator)
            output = processor.process(file_info["buffer"])
            output_filename = file_info["filename"].replace('.docx', '_EN.docx')
            mimetype = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        else:
            processor = XlsxProcessor(translator)
            output = processor.process(file_info["buffer"])
            output_filename = file_info["filename"].replace('.xlsx', '_EN.xlsx')
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        
        processing_time = time.time() - start_time
        
        logger.info(f"Translation completed: {file_info['filename']} -> {output_filename}, "
                   f"time: {processing_time:.2f}s")
        
        response = make_response(send_file(
            output,
            mimetype=mimetype,
            as_attachment=True,
            download_name=output_filename
        ))
        
        response.headers['X-Processing-Time'] = f"{processing_time:.2f}"
        response.headers['X-API-Calls'] = str(translator.stats["api_calls"])
        response.headers['X-Cache-Hits'] = str(translator.stats["cache_hits"])
        
        return response
        
    except Exception as e:
        logger.error(f"Translation failed: {e}", exc_info=True)
        return jsonify({
            "error": "Translation failed",
            "message": "An error occurred. Please try again."
        }), 500

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

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.getenv("PORT", 5000)))
