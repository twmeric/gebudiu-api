#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增強版 DOCX 處理器
集成 Translation Memory 和 領域檢測
"""

import os
import re
import zipfile
import tempfile
import shutil
import gc
import logging
from io import BytesIO
from typing import List, Tuple, Dict

logger = logging.getLogger(__name__)

class EnhancedDocxProcessor:
    """
    增強版 DOCX 處理器
    
    新特性:
    - 領域自動檢測
    - TM優先匹配
    - 翻譯質量追蹤
    """
    
    def __init__(self, translator):
        self.translator = translator
        self.stats = {
            "paragraphs": 0,
            "tables": 0,
            "cells": 0,
            "media_skipped": 0,
            "tm_hits": 0,
            "api_calls": 0
        }
    
    def process(self, file_buffer: bytes, filename: str = None) -> BytesIO:
        """
        處理 DOCX 文件
        
        Args:
            file_buffer: 文件內容
            filename: 文件名 (用於領域檢測)
            
        Returns:
            BytesIO: 翻譯後的文件
        """
        # 使用臨時文件處理
        with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as temp_input:
            temp_input.write(file_buffer)
            temp_input_path = temp_input.name
        
        temp_output_path = temp_input_path.replace('.docx', '_translated.docx')
        
        try:
            # 提取前幾段文字用於領域檢測
            domain_samples = self._extract_samples_for_domain(temp_input_path)
            
            # 檢測領域
            if filename and hasattr(self.translator, 'detect_domain'):
                detected_domain = self.translator.detect_domain(filename, domain_samples)
                logger.info(f"Processing {filename} with domain: {detected_domain}")
            
            # 流式處理
            self._process_streaming(temp_input_path, temp_output_path)
            
            # 讀取結果
            with open(temp_output_path, 'rb') as f:
                result = BytesIO(f.read())
            
            gc.collect()
            return result
            
        finally:
            # 清理臨時文件
            try:
                os.unlink(temp_input_path)
                if os.path.exists(temp_output_path):
                    os.unlink(temp_output_path)
            except:
                pass
    
    def _extract_samples_for_domain(self, docx_path: str) -> List[str]:
        """提取樣本用於領域檢測"""
        samples = []
        
        try:
            with zipfile.ZipFile(docx_path, 'r') as zf:
                # 優先讀取 document.xml
                if 'word/document.xml' in zf.namelist():
                    with zf.open('word/document.xml') as f:
                        content = f.read().decode('utf-8', errors='ignore')
                        # 提取前 5 個 <w:t> 標籤內容
                        pattern = r'<w:t[^>]*>([^<]+)</w:t>'
                        matches = re.findall(pattern, content)
                        samples = [m.strip() for m in matches[:5] if len(m.strip()) > 2]
        except:
            pass
        
        return samples
    
    def _process_streaming(self, input_path: str, output_path: str):
        """流式處理核心"""
        # 1. 掃描 ZIP 內容
        media_files = []
        xml_files = []
        
        with zipfile.ZipFile(input_path, 'r') as zf:
            for info in zf.infolist():
                if info.filename.startswith('word/media/'):
                    media_files.append(info.filename)
                    self.stats["media_skipped"] += info.file_size
                elif info.filename.endswith('.xml'):
                    xml_files.append(info.filename)
        
        logger.info(f"Found {len(media_files)} media files, {len(xml_files)} XML files")
        
        # 2. 提取所有需要翻譯的文本
        texts_to_translate = []
        xml_text_map = {}
        
        for xml_file in xml_files:
            texts, mappings = self._extract_texts_from_xml(input_path, xml_file)
            if texts:
                texts_to_translate.extend(texts)
                xml_text_map[xml_file] = mappings
        
        logger.info(f"Collected {len(texts_to_translate)} texts to translate")
        
        if not texts_to_translate:
            shutil.copy(input_path, output_path)
            return
        
        # 3. 批量翻譯 (使用增強服務)
        translations = self._translate_texts(texts_to_translate)
        translation_map = dict(zip(texts_to_translate, translations))
        
        # 4. 流式重建 DOCX
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as out_zf:
            with zipfile.ZipFile(input_path, 'r') as in_zf:
                
                # 4.1 直接複製媒體文件
                for media_file in media_files:
                    with in_zf.open(media_file) as src:
                        out_zf.writestr(media_file, src.read())
                
                # 4.2 處理 XML 文件
                for xml_file in xml_files:
                    if xml_file in xml_text_map:
                        modified_xml = self._modify_xml_content(
                            in_zf, xml_file, xml_text_map[xml_file], translation_map
                        )
                        out_zf.writestr(xml_file, modified_xml)
                    else:
                        with in_zf.open(xml_file) as src:
                            out_zf.writestr(xml_file, src.read())
                
                # 4.3 複製其他文件
                for item in in_zf.namelist():
                    if item not in media_files and item not in xml_files:
                        with in_zf.open(item) as src:
                            out_zf.writestr(item, src.read())
    
    def _extract_texts_from_xml(self, docx_path: str, xml_file: str) -> Tuple[List[str], List[Tuple[str, int]]]:
        """從 XML 中提取文本"""
        texts = []
        mappings = []
        
        with zipfile.ZipFile(docx_path, 'r') as zf:
            with zf.open(xml_file) as f:
                content = f.read().decode('utf-8')
        
        pattern = r'<w:t[^>]*>([^<]+)</w:t>'
        matches = list(re.finditer(pattern, content))
        
        for idx, match in enumerate(matches):
            text = match.group(1)
            if text.strip() and self._should_translate(text):
                texts.append(text)
                mappings.append((text, idx))
                self.stats["paragraphs"] += 1
        
        return texts, mappings
    
    def _should_translate(self, text: str) -> bool:
        """判斷是否需要翻譯"""
        if not text or len(text.strip()) < 2:
            return False
        
        text = text.strip()
        
        if text.isdigit():
            return False
        
        if text.startswith(('http://', 'https://')):
            return False
        
        if '@' in text and '.' in text.split('@')[-1]:
            return False
        
        if re.match(r'^G-\d+$', text):
            return False
        
        return True
    
    def _translate_texts(self, texts: List[str]) -> List[str]:
        """批量翻譯文本"""
        if not texts:
            return []
        
        # 去重
        seen = {}
        unique_texts = []
        for text in texts:
            if text not in seen:
                seen[text] = len(unique_texts)
                unique_texts.append(text)
        
        # 批量翻譯
        translated_unique = []
        batch_size = 8
        
        for i in range(0, len(unique_texts), batch_size):
            batch = unique_texts[i:i+batch_size]
            
            # 使用增強服務翻譯
            if hasattr(self.translator, 'translate_batch'):
                # 增強版服務
                results = self.translator.translate_batch(
                    [(f"item_{j}", t) for j, t in enumerate(batch)]
                )
                batch_translated = [results.get(f"item_{j}", type('obj', (object,), {'text': batch[j]})).text 
                                   for j in range(len(batch))]
            else:
                # 舊版服務
                batch_translated = []
                for text in batch:
                    translated, _ = self.translator.translate_text(text)
                    batch_translated.append(translated)
            
            translated_unique.extend(batch_translated)
        
        # 映射回原順序
        return [translated_unique[seen[text]] for text in texts]
    
    def _modify_xml_content(self, in_zf: zipfile.ZipFile, xml_file: str,
                           mappings: List[Tuple[str, int]], translation_map: Dict[str, str]) -> bytes:
        """修改 XML 內容"""
        with in_zf.open(xml_file) as f:
            content = f.read().decode('utf-8')
        
        # 構建替換映射
        replacements = []
        for original_text, idx in mappings:
            if original_text in translation_map:
                translated = translation_map[original_text]
                if translated != original_text:
                    replacements.append((original_text, translated))
        
        # 按長度降序排序
        replacements.sort(key=lambda x: len(x[0]), reverse=True)
        
        # 執行替換
        for original, translated in replacements:
            old_pattern = f'<w:t([^>]*)>{re.escape(original)}</w:t>'
            new_replacement = f'<w:t\\1>{translated}</w:t>'
            content = re.sub(old_pattern, new_replacement, content)
        
        return content.encode('utf-8')
    
    def get_stats(self) -> Dict:
        """獲取處理統計"""
        return self.stats.copy()


if __name__ == "__main__":
    # 測試
    logging.basicConfig(level=logging.INFO)
    
    # 這裡需要一個翻譯服務實例來測試
    print("EnhancedDocxProcessor ready for testing")
