#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
舊格式文件處理器 (.doc, .xls)
提供向下兼容支持
"""

import logging
import os
from io import BytesIO

try:
    import xlrd
    XLRD_AVAILABLE = True
except ImportError:
    XLRD_AVAILABLE = False

try:
    import textract
    TEXTRACT_AVAILABLE = True
except ImportError:
    TEXTRACT_AVAILABLE = False

logger = logging.getLogger(__name__)

class LegacyFormatHandler:
    """處理舊格式文件 (.doc, .xls)"""
    
    # 文件頭識別
    OLD_DOC_HEADER = b'\xd0\xcf\x11\xe0'  # .doc OLE格式
    OLD_XLS_HEADER = b'\xd0\xcf\x11\xe0'  # .xls OLE格式 (與.doc相同頭)
    
    @staticmethod
    def is_old_doc(file_bytes: bytes) -> bool:
        """檢測是否為舊格式 .doc"""
        return file_bytes[:4] == LegacyFormatHandler.OLD_DOC_HEADER
    
    @staticmethod
    def is_old_xls(file_bytes: bytes) -> bool:
        """檢測是否為舊格式 .xls"""
        # 通過文件內容特徵判斷
        if file_bytes[:4] != LegacyFormatHandler.OLD_XLS_HEADER:
            return False
        
        # .xls 和 .doc 有相同的文件頭，需要進一步判斷
        # 檢查是否包含 Excel 特有的標識
        try:
            content = file_bytes[:1000].decode('latin-1', errors='ignore')
            excel_markers = ['Workbook', 'Sheet', 'Excel', 'xls']
            return any(marker in content for marker in excel_markers)
        except:
            return False
    
    @staticmethod
    def extract_text_from_xls(file_bytes: bytes) -> str:
        """
        從 .xls 文件提取文本
        使用 xlrd 庫（純 Python，Render 兼容）
        """
        if not XLRD_AVAILABLE:
            raise ImportError("xlrd not installed. Run: pip install xlrd")
        
        try:
            workbook = xlrd.open_workbook(file_contents=file_bytes)
            text_parts = []
            
            for sheet_idx in range(workbook.nsheets):
                sheet = workbook.sheet_by_index(sheet_idx)
                text_parts.append(f"=== Sheet: {sheet.name} ===")
                
                for row_idx in range(sheet.nrows):
                    row_values = []
                    for col_idx in range(sheet.ncols):
                        cell_value = sheet.cell_value(row_idx, col_idx)
                        if cell_value:
                            row_values.append(str(cell_value))
                    if row_values:
                        text_parts.append("\t".join(row_values))
            
            return "\n".join(text_parts)
        
        except Exception as e:
            logger.error(f"Failed to extract text from .xls: {e}")
            raise
    
    @staticmethod
    def extract_text_from_doc(file_bytes: bytes) -> str:
        """
        從 .doc 文件提取文本
        嘗試使用 textract，否則使用備選方案
        """
        if TEXTRACT_AVAILABLE:
            try:
                # textract 需要文件路徑，我們創建臨時文件
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.doc', delete=False) as tmp:
                    tmp.write(file_bytes)
                    tmp_path = tmp.name
                
                text = textract.process(tmp_path).decode('utf-8', errors='ignore')
                os.unlink(tmp_path)
                return text
            except Exception as e:
                logger.warning(f"textract failed: {e}, trying fallback")
        
        # 備選方案：基本文本提取
        return LegacyFormatHandler._basic_doc_extract(file_bytes)
    
    @staticmethod
    def _basic_doc_extract(file_bytes: bytes) -> str:
        """
        基本的 .doc 文本提取（不依賴外部工具）
        從二進制數據中提取可打印文本
        """
        try:
            # 解碼為 latin-1，提取可打印字符
            text = file_bytes.decode('latin-1', errors='ignore')
            
            # 過濾可打印文本（長度大於 3 的連續字符）
            import re
            # 匹配中文字符、英文字詞、數字
            pattern = r'[\u4e00-\u9fa5]{2,}|[a-zA-Z]{3,}|\d{2,}'
            matches = re.findall(pattern, text)
            
            # 去重並組合
            seen = set()
            unique_texts = []
            for match in matches:
                if match not in seen and len(match) > 3:
                    seen.add(match)
                    unique_texts.append(match)
            
            return "\n".join(unique_texts[:1000])  # 限制數量
        
        except Exception as e:
            logger.error(f"Basic doc extract failed: {e}")
            return ""
    
    @classmethod
    def convert_to_docx_text(cls, file_bytes: bytes, original_ext: str) -> str:
        """
        統一接口：將舊格式文件轉換為文本
        
        Args:
            file_bytes: 文件內容
            original_ext: 原始文件擴展名 (.doc 或 .xls)
        
        Returns:
            提取的文本內容
        """
        original_ext = original_ext.lower()
        
        if original_ext == '.xls':
            if XLRD_AVAILABLE:
                return cls.extract_text_from_xls(file_bytes)
            else:
                raise RuntimeError(
                    "不支持舊格式 .xls，請使用以下方法轉換：\n"
                    "1. 在 Excel 中打開，另存為 .xlsx\n"
                    "2. 使用在線轉換工具：https://convertio.co/zh/xls-xlsx/"
                )
        
        elif original_ext == '.doc':
            # 嘗試提取文本，但質量可能不佳
            text = cls.extract_text_from_doc(file_bytes)
            if text:
                return text
            else:
                raise RuntimeError(
                    "無法讀取舊格式 .doc，建議轉換為 .docx 後重試：\n"
                    "1. 在 Word 中打開，另存為 .docx\n"
                    "2. 使用在線轉換工具：https://convertio.co/zh/doc-docx/"
                )
        
        else:
            raise ValueError(f"Unsupported legacy format: {original_ext}")


# 使用建議和轉換工具
CONVERSION_TOOLS = {
    '.doc': {
        'name': 'Word 文檔',
        'methods': [
            {
                'name': 'Microsoft Word',
                'steps': [
                    '用 Word 打開文件',
                    '點擊「文件」→「另存為」',
                    '選擇格式：「Word 文檔 (*.docx)」',
                    '保存並上傳新文件'
                ]
            },
            {
                'name': 'WPS Office',
                'steps': [
                    '用 WPS 打開文件',
                    '點擊「另存為」',
                    '選擇 .docx 格式',
                    '保存並上傳'
                ]
            },
            {
                'name': '在線轉換工具',
                'urls': [
                    'https://convertio.co/zh/doc-docx/',
                    'https://cloudconvert.com/doc-to-docx'
                ]
            }
        ]
    },
    '.xls': {
        'name': 'Excel 表格',
        'methods': [
            {
                'name': 'Microsoft Excel',
                'steps': [
                    '用 Excel 打開文件',
                    '點擊「文件」→「另存為」',
                    '選擇格式：「Excel 工作簿 (*.xlsx)」',
                    '保存並上傳新文件'
                ]
            },
            {
                'name': 'WPS 表格',
                'steps': [
                    '用 WPS 打開文件',
                    '點擊「另存為」',
                    '選擇 .xlsx 格式',
                    '保存並上傳'
                ]
            },
            {
                'name': '在線轉換工具',
                'urls': [
                    'https://convertio.co/zh/xls-xlsx/',
                    'https://cloudconvert.com/xls-to-xlsx'
                ]
            }
        ]
    }
}


def get_conversion_guide(file_ext: str) -> str:
    """獲取格式轉換指南"""
    file_ext = file_ext.lower()
    info = CONVERSION_TOOLS.get(file_ext)
    
    if not info:
        return "暫不支持此格式"
    
    guide_lines = [
        f"檢測到舊格式 {file_ext}（{info['name']}）",
        "",
        "為獲得最佳翻譯效果，建議轉換為新格式：",
        ""
    ]
    
    for idx, method in enumerate(info['methods'], 1):
        guide_lines.append(f"{idx}. {method['name']}")
        
        if 'steps' in method:
            for step in method['steps']:
                guide_lines.append(f"   • {step}")
        
        if 'urls' in method:
            guide_lines.append("   在線工具：")
            for url in method['urls']:
                guide_lines.append(f"   • {url}")
        
        guide_lines.append("")
    
    guide_lines.append("轉換後重新上傳即可獲得完整格式保留功能！")
    
    return "\n".join(guide_lines)
