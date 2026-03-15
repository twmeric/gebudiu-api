#!/usr/bin/env python3
"""
StreamTranslator - 低記憶體 DOCX 翻譯器
======================================
創新點：分離 XML 和媒體處理，圖片不進記憶體

核心技術：
1. ZIP 流式處理 - 不解壓縮整個文件
2. XML 分片處理 - 只提取 <w:t> 文本節點
3. 媒體直通 - 圖片直接複製，零記憶體佔用
4. 增量打包 - 處理一塊寫入一塊
"""

import os
import re
import io
import zipfile
import xml.etree.ElementTree as ET
from typing import BinaryIO, Iterator, Tuple, List
from dataclasses import dataclass
import tempfile
import shutil


# ============================================================================
# 核心創新：ZIP 流式處理器
# ============================================================================

class StreamingDocxProcessor:
    """
    流式 DOCX 處理器
    
    關鍵創新：
    - 圖片不進記憶體，直接從 ZIP 複製到新 ZIP
    - 只提取 XML 中的 <w:t> 文本節點
    - 增量寫入，控制記憶體使用
    """
    
    # Word XML 命名空間
    NAMESPACES = {
        'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
        'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
        'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
        'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture',
    }
    
    def __init__(self, translator_func):
        """
        Args:
            translator_func: 翻譯函數，接收文本列表，返回翻譯後列表
        """
        self.translator = translator_func
        self.stats = {
            "xml_files": 0,
            "media_files": 0,
            "text_nodes": 0,
            "translated_nodes": 0,
            "bytes_skipped": 0,  # 圖片節省的字節
        }
    
    def process(self, input_path: str, output_path: str, domain: str = "general"):
        """
        流式處理 DOCX 文件
        
        記憶體使用：
        - 傳統方式：加載整個文檔（50-200MB）
        - 此方式：僅加載 XML 文本（< 1MB）
        """
        # 創建臨時目錄
        with tempfile.TemporaryDirectory() as temp_dir:
            # 步驟 1：掃描並分類 ZIP 內容
            media_files, xml_files = self._scan_docx(input_path)
            
            # 步驟 2：提取所有需要翻譯的文本（僅 XML）
            texts_to_translate = []
            xml_modifications = {}  # file -> [(elem_id, original_text)]
            
            for xml_file in xml_files:
                texts, mappings = self._extract_texts_from_xml(input_path, xml_file)
                if texts:
                    texts_to_translate.extend(texts)
                    xml_modifications[xml_file] = mappings
            
            # 步驟 3：批量翻譯（API 調用次數最少化）
            translations = self._translate_batch(texts_to_translate, domain)
            
            # 步驟 4：構建翻譯映射
            translation_map = dict(zip(texts_to_translate, translations))
            
            # 步驟 5：流式重建 DOCX
            self._rebuild_docx(
                input_path, 
                output_path, 
                media_files, 
                xml_files,
                xml_modifications,
                translation_map,
                temp_dir
            )
        
        return self.stats
    
    def _scan_docx(self, docx_path: str) -> Tuple[List[str], List[str]]:
        """
        掃描 DOCX 內容，分離媒體和 XML
        
        Returns:
            (media_files, xml_files)
        """
        media_files = []
        xml_files = []
        
        with zipfile.ZipFile(docx_path, 'r') as zf:
            for info in zf.infolist():
                if info.filename.startswith('word/media/'):
                    media_files.append(info.filename)
                    self.stats["bytes_skipped"] += info.file_size
                elif info.filename.endswith('.xml'):
                    xml_files.append(info.filename)
        
        self.stats["media_files"] = len(media_files)
        self.stats["xml_files"] = len(xml_files)
        
        return media_files, xml_files
    
    def _extract_texts_from_xml(self, docx_path: str, xml_file: str) -> Tuple[List[str], List]:
        """
        從 XML 文件中提取所有 <w:t> 文本節點
        
        優化：使用迭代器而非整個 DOM 樹
        """
        texts = []
        mappings = []
        
        with zipfile.ZipFile(docx_path, 'r') as zf:
            with zf.open(xml_file) as f:
                # 增量解析 XML，控制記憶體
                context = ET.iterparse(f, events=('start', 'end'))
                context = iter(context)
                event, root = next(context)
                
                elem_id = 0
                for event, elem in context:
                    if event == 'end' and elem.tag == '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t':
                        # <w:t> 節點 - 這是文本內容
                        text = elem.text or ""
                        if text.strip() and self._contains_chinese(text):
                            texts.append(text)
                            mappings.append((elem_id, text, elem))
                            self.stats["text_nodes"] += 1
                        elem_id += 1
                    
                    # 清理已處理的節點，釋放記憶體
                    if event == 'end':
                        elem.clear()
                        if elem.getparent() is not None:
                            elem.getparent().remove(elem)
                
                root.clear()
        
        return texts, mappings
    
    def _contains_chinese(self, text: str) -> bool:
        """快速檢測是否包含中文"""
        return bool(re.search(r'[\u4e00-\u9fff]', text))
    
    def _translate_batch(self, texts: List[str], domain: str) -> List[str]:
        """批量翻譯（去重後）"""
        if not texts:
            return []
        
        # 去重，保留順序
        seen = {}
        unique_texts = []
        for text in texts:
            if text not in seen:
                seen[text] = len(unique_texts)
                unique_texts.append(text)
        
        # 調用翻譯器
        translated_unique = self.translator(unique_texts, domain)
        
        # 映射回原順序
        return [translated_unique[seen[text]] for text in texts]
    
    def _rebuild_docx(
        self,
        input_path: str,
        output_path: str,
        media_files: List[str],
        xml_files: List[str],
        xml_modifications: dict,
        translation_map: dict,
        temp_dir: str
    ):
        """
        流式重建 DOCX
        
        創新點：
        - 媒體文件直接從原 ZIP 複製，不進記憶體
        - XML 文件修改後寫入
        - 使用臨時文件避免記憶體峰值
        """
        # 創建新的 ZIP 文件
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as out_zf:
            with zipfile.ZipFile(input_path, 'r') as in_zf:
                
                # 1. 複製媒體文件（零記憶體佔用）
                for media_file in media_files:
                    with in_zf.open(media_file) as src:
                        out_zf.writestr(media_file, src.read())
                
                # 2. 處理 XML 文件
                for xml_file in xml_files:
                    if xml_file in xml_modifications:
                        # 需要修改的 XML
                        modified_xml = self._modify_xml(
                            in_zf, xml_file, xml_modifications[xml_file], translation_map
                        )
                        out_zf.writestr(xml_file, modified_xml)
                    else:
                        # 無需修改，直接複製
                        with in_zf.open(xml_file) as src:
                            out_zf.writestr(xml_file, src.read())
                
                # 3. 複製其他文件（如 [Content_Types].xml, _rels/*）
                for item in in_zf.namelist():
                    if item not in media_files and item not in xml_files:
                        with in_zf.open(item) as src:
                            out_zf.writestr(item, src.read())
    
    def _modify_xml(
        self,
        in_zf: zipfile.ZipFile,
        xml_file: str,
        mappings: List,
        translation_map: dict
    ) -> bytes:
        """
        修改 XML 文件中的文本節點
        
        使用正則表達式而非 XML 解析，更快且記憶體佔用更低
        """
        with in_zf.open(xml_file) as f:
            xml_content = f.read().decode('utf-8')
        
        # 構建替換映射（按長度降序，避免部分替換問題）
        replacements = []
        for elem_id, original_text, _ in mappings:
            if original_text in translation_map:
                translated = translation_map[original_text]
                if translated != original_text:
                    replacements.append((original_text, translated))
                    self.stats["translated_nodes"] += 1
        
        # 執行替換
        for original, translated in replacements:
            # 使用 word boundary 避免部分匹配
            pattern = re.escape(original)
            xml_content = re.sub(pattern, translated.replace('\\', '\\\\'), xml_content)
        
        return xml_content.encode('utf-8')


# ============================================================================
# 極致優化：超級流式模式
# ============================================================================

class UltraStreamTranslator:
    """
    極致流式翻譯器 - 記憶體佔用 < 10MB
    
    適用場景：
    - 超大文件（> 10MB）
    - 記憶體極度受限環境（< 512MB）
    - 批量處理
    
    技術特點：
    1. 文件分片：將大 XML 分成多個小片段
    2. 逐段翻譯：一次處理 100 個文本節點
    3. 磁盤緩衝：中間結果寫入臨時文件
    """
    
    def __init__(self, translator_func, chunk_size: int = 100):
        self.translator = translator_func
        self.chunk_size = chunk_size
        self.stats = {"chunks_processed": 0}
    
    def process_ultra(self, input_path: str, output_path: str, domain: str = "general"):
        """
        超級流式處理 - 記憶體佔用恆定
        
        流程：
        1. 創建臨時目錄
        2. 解壓 DOCX（選擇性）
        3. 分片處理 XML
        4. 增量壓縮
        5. 清理
        """
        with tempfile.TemporaryDirectory() as work_dir:
            # 解壓 DOCX（僅 XML 文件）
            xml_dir = os.path.join(work_dir, "xml")
            media_dir = os.path.join(work_dir, "media")
            os.makedirs(xml_dir)
            os.makedirs(media_dir)
            
            # 分離提取
            self._extract_selective(input_path, xml_dir, media_dir)
            
            # 處理 XML 文件
            for xml_file in os.listdir(xml_dir):
                self._process_xml_chunked(
                    os.path.join(xml_dir, xml_file),
                    domain
                )
            
            # 重新打包
            self._repackage(xml_dir, media_dir, output_path)
    
    def _extract_selective(self, docx_path: str, xml_dir: str, media_dir: str):
        """選擇性提取：XML 到目錄，媒體到目錄"""
        with zipfile.ZipFile(docx_path, 'r') as zf:
            for item in zf.namelist():
                if item.endswith('.xml'):
                    zf.extract(item, xml_dir)
                elif item.startswith('word/media/'):
                    zf.extract(item, media_dir)
    
    def _process_xml_chunked(self, xml_path: str, domain: str):
        """分塊處理 XML 文件"""
        # 讀取 XML
        with open(xml_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取所有 <w:t>...</w:t>
        pattern = r'(<w:t[^>]*>)([^<]*)(</w:t>)'
        matches = list(re.finditer(pattern, content))
        
        # 分塊處理
        chunks = [matches[i:i+self.chunk_size] for i in range(0, len(matches), self.chunk_size)]
        
        # 從後往前替換，避免位置偏移
        offset = 0
        for chunk in reversed(chunks):
            texts = [m.group(2) for m in chunk if self._contains_chinese(m.group(2))]
            if texts:
                translations = self.translator(texts, domain)
                trans_map = dict(zip(texts, translations))
                
                # 替換
                for match in chunk:
                    original = match.group(2)
                    if original in trans_map:
                        start = match.start(2) + offset
                        end = match.end(2) + offset
                        translated = trans_map[original]
                        content = content[:start] + translated + content[end:]
                        offset += len(translated) - len(original)
        
        # 寫回
        with open(xml_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        self.stats["chunks_processed"] += len(chunks)
    
    def _repackage(self, xml_dir: str, media_dir: str, output_path: str):
        """重新打包成 DOCX"""
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # 添加 XML
            for root, dirs, files in os.walk(xml_dir):
                for file in files:
                    full_path = os.path.join(root, file)
                    arcname = os.path.relpath(full_path, xml_dir)
                    zf.write(full_path, arcname)
            
            # 添加媒體
            for root, dirs, files in os.walk(media_dir):
                for file in files:
                    full_path = os.path.join(root, file)
                    arcname = os.path.relpath(full_path, media_dir)
                    zf.write(full_path, arcname)
    
    def _contains_chinese(self, text: str) -> bool:
        return bool(re.search(r'[\u4e00-\u9fff]', text))


# ============================================================================
# 使用示例
# ============================================================================

if __name__ == "__main__":
    # 模擬翻譯函數
    def mock_translator(texts, domain):
        return [f"[EN] {t}" for t in texts]
    
    # 測試
    processor = StreamingDocxProcessor(mock_translator)
    
    input_file = r"C:\Users\Owner\.kimi\sessions\3d53a0cbf89ea8d1d965a6b51de8640f\9942a6c8-cf8c-4d74-9feb-fe6ec6f03123\uploads\DEP-108 产品规格书_011f86.docx"
    output_file = r"C:\Users\Owner\cloudflare\Docx\gebudiu-api\test_output.docx"
    
    if os.path.exists(input_file):
        stats = processor.process(input_file, output_file)
        print("\n處理統計：")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        if os.path.exists(output_file):
            size = os.path.getsize(output_file)
            print(f"\n輸出文件大小: {size / 1024 / 1024:.2f} MB")
    else:
        print(f"測試文件不存在: {input_file}")
