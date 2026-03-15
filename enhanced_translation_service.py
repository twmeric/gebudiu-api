#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增強版翻譯服務
集成 Translation Memory + Domain Detection + 術語表管理
"""

import os
import re
import json
import logging
import hashlib
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass

from translation_memory import TranslationMemory, get_translation_memory
from domain_detector import DomainDetector, DomainPromptEnhancer, get_domain_detector
from terminology_manager import TerminologyManager, get_terminology_manager

logger = logging.getLogger(__name__)

@dataclass
class TranslationResult:
    """翻譯結果"""
    text: str
    source: str
    is_cached: bool = False
    is_tm_match: bool = False
    similarity: float = 0.0
    domain: str = "general"
    quality_score: float = 0.0

class EnhancedTranslationService:
    """
    增強版翻譯服務
    
    特性:
    1. Translation Memory 優先匹配
    2. 智能領域檢測
    3. 術語表管理
    4. 翻譯質量評分
    """
    
    # Prompt 模板
    PROMPTS = {
        "general": "You are a professional translator. Translate the following Chinese text to English for general business use. Provide ONLY the English translation.",
        "electronics": "You are an electronics industry translator. Use standard technical terminology. Preserve model numbers and specifications. Provide ONLY the English translation.",
        "medical": "You are a medical device translator. Use formal, cautious medical terminology suitable for regulatory compliance. Provide ONLY the English translation.",
        "legal": "You are a legal contract translator. Use precise legal terminology and formal contractual language. Provide ONLY the English translation.",
        "marketing": "You are a marketing copy translator. Make the content persuasive and appealing. Provide ONLY the English translation.",
        "industrial": "You are an industrial/technical translator. Use ISO-standard terminology. Provide ONLY the English translation.",
        "software": "You are a software/IT documentation translator. Preserve code snippets and API names. Provide ONLY the English translation."
    }
    
    def __init__(self, domain: str = "general", use_tm: bool = True, 
                 tm_threshold: float = 0.85, auto_detect_domain: bool = True,
                 use_terminology: bool = True):
        """
        初始化增強版翻譯服務
        
        Args:
            domain: 默認領域
            use_tm: 是否使用Translation Memory
            tm_threshold: TM匹配閾值
            auto_detect_domain: 是否自動檢測領域
            use_terminology: 是否使用術語表管理
        """
        self.domain = domain
        self.use_tm = use_tm
        self.tm_threshold = tm_threshold
        self.auto_detect_domain = auto_detect_domain
        self.use_terminology = use_terminology
        
        # 初始化組件
        self.tm = get_translation_memory() if use_tm else None
        self.domain_detector = get_domain_detector()
        self.prompt_enhancer = DomainPromptEnhancer()
        self.terminology_manager = get_terminology_manager() if use_terminology else None
        
        # 統計
        self.stats = {
            "api_calls": 0,
            "tm_hits": 0,
            "cache_hits": 0,
            "tokens_saved": 0,
            "domain_switches": 0,
            "terminology_hits": 0
        }
        
        logger.info(f"EnhancedTranslationService initialized: domain={domain}, use_tm={use_tm}, use_terminology={use_terminology}")
    
    def detect_domain(self, filename: str, content_samples: List[str] = None) -> str:
        """
        檢測文檔領域
        
        Args:
            filename: 文件名
            content_samples: 內容樣本
            
        Returns:
            str: 檢測到的領域
        """
        if not self.auto_detect_domain:
            return self.domain
        
        detected_domain, confidence = self.domain_detector.detect(filename, content_samples)
        
        if detected_domain != self.domain:
            logger.info(f"Domain detected: {self.domain} -> {detected_domain} (confidence: {confidence:.2f})")
            self.stats["domain_switches"] += 1
        
        return detected_domain
    
    def translate_batch(self, texts: List[Tuple[str, str]], 
                       filename: str = None,
                       max_retries: int = 2) -> Dict[str, TranslationResult]:
        """
        批量翻譯 - 增強版
        
        Args:
            texts: [(id, text), ...]
            filename: 文件名 (用於領域檢測)
            max_retries: 最大重試次數
            
        Returns:
            Dict[str, TranslationResult]: {id: TranslationResult}
        """
        if not texts:
            return {}
        
        # 1. 領域檢測 (基於文件名和前幾個文本樣本)
        content_samples = [text for _, text in texts[:5]]
        detected_domain = self.detect_domain(filename or "", content_samples)
        self.domain = detected_domain
        
        # 2. 先檢查TM和緩存
        results = {}
        to_translate = []
        
        for item_id, text in texts:
            if not self._should_translate(text):
                results[item_id] = TranslationResult(
                    text=text,
                    source=text,
                    is_cached=True,
                    domain=detected_domain
                )
                continue
            
            # 檢查TM
            if self.use_tm and self.tm:
                tm_results = self.tm.search(text, detected_domain)
                if tm_results and tm_results[0].similarity >= self.tm_threshold:
                    best_match = tm_results[0]
                    results[item_id] = TranslationResult(
                        text=best_match.target,
                        source=text,
                        is_tm_match=True,
                        similarity=best_match.similarity,
                        domain=detected_domain
                    )
                    self.stats["tm_hits"] += 1
                    self.stats["tokens_saved"] += len(text) * 1.5
                    continue
            
            to_translate.append((item_id, text))
        
        # 3. API翻譯剩餘文本
        if to_translate:
            api_results = self._translate_via_api(to_translate, detected_domain, max_retries)
            results.update(api_results)
        
        return results
    
    def _translate_via_api(self, texts: List[Tuple[str, str]], 
                          domain: str, max_retries: int) -> Dict[str, TranslationResult]:
        """通過API翻譯"""
        from openai import OpenAI
        
        results = {}
        
        # 術語預處理 - 保護術語
        preprocessed_texts = []
        marker_maps = []
        
        for item_id, text in texts:
            if self.use_terminology and self.terminology_manager:
                processed, marker_map = self.preprocess_with_terminology(text)
                preprocessed_texts.append((item_id, processed))
                marker_maps.append((item_id, marker_map))
            else:
                preprocessed_texts.append((item_id, text))
                marker_maps.append((item_id, {}))
        
        # 獲取Prompt
        base_prompt = self.PROMPTS.get(domain, self.PROMPTS["general"])
        enhanced_prompt = self.prompt_enhancer.enhance_prompt(base_prompt, domain)
        
        # 構建批量請求 (使用預處理後的文本)
        batch_text = "\n".join([f"[{i}] {text[:500]}" for i, (_, text) in enumerate(preprocessed_texts)])
        
        api_key = os.getenv("DEEPSEEK_API_KEY")
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
        
        for attempt in range(max_retries):
            try:
                logger.info(f"API batch translating {len(texts)} texts, attempt {attempt+1}")
                
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": enhanced_prompt},
                        {"role": "user", "content": f"Translate to English (prefix with [number]):\n{batch_text}\n\nFormat: [0] Translation"}
                    ],
                    temperature=0.3,
                    max_tokens=2000,
                    timeout=60
                )
                
                # 解析結果
                raw_output = response.choices[0].message.content.strip()
                translations = self._parse_batch_output(raw_output, len(texts))
                
                # 處理結果並保存到TM
                for i, (item_id, original) in enumerate(texts):
                    translated = translations.get(i, preprocessed_texts[i][1])
                    
                    # 術語後處理 - 還原術語
                    _, marker_map = marker_maps[i]
                    if marker_map:
                        translated = self.postprocess_with_terminology(translated, marker_map)
                    
                    # 後處理
                    translated = self.prompt_enhancer.post_process(translated, domain)
                    
                    # 質量評分
                    quality = self._evaluate_quality(original, translated)
                    
                    results[item_id] = TranslationResult(
                        text=translated,
                        source=original,
                        quality_score=quality,
                        domain=domain
                    )
                    
                    # 保存到TM
                    if self.use_tm and self.tm and translated != original:
                        self.tm.add(original, translated, domain)
                
                self.stats["api_calls"] += 1
                break
                
            except Exception as e:
                logger.error(f"API translation attempt {attempt+1} failed: {e}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(2 ** attempt)
                else:
                    # 失敗則返回原文
                    for item_id, original in texts:
                        results[item_id] = TranslationResult(
                            text=original,
                            source=original,
                            domain=domain
                        )
        
        return results
    
    def _parse_batch_output(self, output: str, expected_count: int) -> Dict[int, str]:
        """解析批量翻譯輸出"""
        results = {}
        pattern = r'\[(\d+)\]\s*(.+?)(?=\[\d+\]|$)'
        matches = re.findall(pattern, output, re.DOTALL)
        
        for idx_str, text in matches:
            idx = int(idx_str)
            if idx < expected_count:
                results[idx] = text.strip()
        
        return results
    
    def _should_translate(self, text: str) -> bool:
        """判斷是否需要翻譯"""
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
    
    def _evaluate_quality(self, source: str, target: str) -> float:
        """
        評估翻譯質量
        
        Returns:
            float: 質量分數 (0-1)
        """
        score = 0.5  # 基礎分
        
        # 1. 長度合理性
        source_len = len(source)
        target_len = len(target)
        
        if source_len > 0:
            ratio = target_len / source_len
            # 英文通常比中文長 1.2-1.8 倍
            if 0.8 <= ratio <= 3.0:
                score += 0.2
        
        # 2. 關鍵詞保留檢查
        # 檢查數字、型號等是否保留
        source_numbers = re.findall(r'\d+\.?\d*', source)
        target_numbers = re.findall(r'\d+\.?\d*', target)
        if len(source_numbers) == len(target_numbers):
            score += 0.15
        
        # 3. 格式檢查
        if source.count('\n') == target.count('\n'):
            score += 0.15
        
        return min(score, 1.0)
    
    def translate_text(self, text: str) -> Tuple[str, bool]:
        """兼容舊接口 - 單條翻譯"""
        result = self.translate_batch([("single", text)])
        tr = result.get("single")
        if tr:
            return tr.text, tr.is_tm_match or tr.is_cached
        return text, False
    
    def get_stats_report(self) -> Dict:
        """獲取統計報告"""
        total_hits = self.stats["tm_hits"] + self.stats["cache_hits"] + self.stats.get("terminology_hits", 0)
        total_requests = self.stats["api_calls"] + total_hits
        
        hit_rate = (total_hits / max(total_requests, 1)) * 100
        
        report = {
            "api_calls": self.stats["api_calls"],
            "tm_hits": self.stats["tm_hits"],
            "cache_hits": self.stats["cache_hits"],
            "terminology_hits": self.stats.get("terminology_hits", 0),
            "total_hits": total_hits,
            "hit_rate_percent": round(hit_rate, 2),
            "tokens_saved": int(self.stats["tokens_saved"]),
            "domain_switches": self.stats["domain_switches"],
            "current_domain": self.domain,
            "use_terminology": self.use_terminology
        }
        
        # 添加TM統計
        if self.tm:
            report["tm_stats"] = self.tm.get_stats()
        
        # 添加術語表統計
        if self.terminology_manager:
            report["terminology_stats"] = self.terminology_manager.get_stats()
        
        return report
    
    def preprocess_with_terminology(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        使用術語表預處理文本
        
        Args:
            text: 原文
            
        Returns:
            (預處理後文本, 標記映射表)
        """
        if not self.use_terminology or not self.terminology_manager:
            return text, {}
        
        processed, marker_map = self.terminology_manager.preprocess_text(text, self.domain)
        
        if marker_map:
            self.stats["terminology_hits"] += len(marker_map)
            logger.debug(f"Terminology preprocessing: {len(marker_map)} terms protected")
        
        return processed, marker_map
    
    def postprocess_with_terminology(self, text: str, marker_map: Dict[str, str]) -> str:
        """
        使用術語表後處理文本
        
        Args:
            text: 翻譯後文本 (含標記)
            marker_map: 標記映射表
            
        Returns:
            處理後文本
        """
        if not self.use_terminology or not self.terminology_manager or not marker_map:
            return text
        
        processed = self.terminology_manager.postprocess_text(text, marker_map, self.domain)
        return processed
    
    def check_terminology_consistency(self, source_text: str, target_text: str) -> List[Dict]:
        """
        檢查術語一致性
        
        Args:
            source_text: 原文
            target_text: 譯文
            
        Returns:
            不一致列表
        """
        if not self.use_terminology or not self.terminology_manager:
            return []
        
        return self.terminology_manager.check_consistency(source_text, target_text, self.domain)


# 全局服務實例
_service_instance = None

def get_enhanced_translation_service(domain: str = "general") -> EnhancedTranslationService:
    """獲取全局服務實例"""
    global _service_instance
    if _service_instance is None:
        _service_instance = EnhancedTranslationService(domain=domain)
    return _service_instance


if __name__ == "__main__":
    # 測試
    logging.basicConfig(level=logging.INFO)
    
    service = EnhancedTranslationService(domain="general", use_tm=True)
    
    # 測試翻譯
    texts = [
        ("1", "藍牙耳機"),
        ("2", "產品規格書"),
        ("3", "充電器"),
        ("4", "這是一個測試")
    ]
    
    results = service.translate_batch(texts, filename="product_spec.docx")
    
    for item_id, result in results.items():
        print(f"{item_id}: {result.source} -> {result.text}")
        print(f"   TM Match: {result.is_tm_match}, Quality: {result.quality_score:.2f}")
    
    # 再次翻譯 (應該命中TM)
    print("\n--- Second translation (should hit TM) ---")
    results2 = service.translate_batch(texts, filename="product_spec.docx")
    
    for item_id, result in results2.items():
        print(f"{item_id}: {result.source} -> {result.text}")
        print(f"   TM Match: {result.is_tm_match}")
    
    # 統計報告
    print("\n--- Stats Report ---")
    print(json.dumps(service.get_stats_report(), indent=2))
