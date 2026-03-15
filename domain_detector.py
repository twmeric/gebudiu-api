#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能領域檢測器
基於文件名和內容自動識別文檔領域
"""

import re
import logging
from typing import Dict, List, Tuple
from collections import Counter

logger = logging.getLogger(__name__)

class DomainDetector:
    """
    智能領域檢測器
    
    檢測邏輯:
    1. 文件名關鍵詞匹配 (權重: 0.4)
    2. 內容TF-IDF風格分類 (權重: 0.6)
    """
    
    # 領域關鍵詞映射
    DOMAIN_KEYWORDS = {
        "electronics": {
            "filename_keywords": [
                "product", "spec", "規格", "產品", "型號", "model", "datasheet",
                "manual", "user guide", "說明書", "電子", "electronic", "device"
            ],
            "content_keywords": [
                "voltage", "current", "power", "frequency", "input", "output",
                "bluetooth", "wireless", "charging", "battery", "usb", "hdmi",
                "電壓", "電流", "功率", "頻率", "輸入", "輸出", "藍牙", "無線",
                "充電", "電池", "規格", "型號", "尺寸", "重量"
            ],
            "icon": "🔌"
        },
        "medical": {
            "filename_keywords": [
                "medical", "device", "醫療", "器械", "fda", "ce", "iso 13485",
                "clinical", "診斷", "diagnostic", "手術", "surgical"
            ],
            "content_keywords": [
                "patient", "treatment", "diagnosis", "symptom", "disease",
                "clinical", "medical device", "sterilization", "biocompatibility",
                "患者", "治療", "診斷", "症狀", "疾病", "臨床", "醫療器械",
                "滅菌", "生物相容性", "手術", "植入"
            ],
            "icon": "🏥"
        },
        "legal": {
            "filename_keywords": [
                "contract", "agreement", "條款", "合同", "協議", "legal",
                "terms", "conditions", "law", "律師", "條文", "條約"
            ],
            "content_keywords": [
                "party", "clause", "article", "section", "hereby", "pursuant",
                "liability", "indemnification", "jurisdiction", "governing law",
                "雙方", "條款", "條文", "第", "條", "款", "項", "據此",
                "責任", "賠償", "管轄", "適用法律", "合同", "協議"
            ],
            "icon": "⚖️"
        },
        "marketing": {
            "filename_keywords": [
                "marketing", "promotion", "廣告", "宣傳", "推廣", "campaign",
                "brand", "brochure", "catalog", "目錄", "型錄", "dm"
            ],
            "content_keywords": [
                "promotion", "discount", "offer", "campaign", "brand",
                "advertising", "market", "customer", "sales", "revenue",
                "促銷", "折扣", "優惠", "活動", "品牌", "廣告", "市場",
                "客戶", "銷售", "收入", "推廣", "宣傳"
            ],
            "icon": "📢"
        },
        "industrial": {
            "filename_keywords": [
                "industrial", "machinery", "機械", "設備", "製造", "manufacturing",
                "factory", "automation", "自動化", "iso 9001", "quality"
            ],
            "content_keywords": [
                "machine", "equipment", "manufacturing", "production", "factory",
                "industrial", "automation", "process", "assembly", "quality control",
                "機器", "設備", "製造", "生產", "工廠", "工業", "自動化",
                "過程", "組裝", "質量控制", "裝配"
            ],
            "icon": "🏭"
        },
        "software": {
            "filename_keywords": [
                "software", "app", "application", "api", "sdk", "documentation",
                "developer", "programming", "代碼", "軟件", "程序", "開發"
            ],
            "content_keywords": [
                "api", "function", "method", "class", "variable", "database",
                "server", "client", "request", "response", "json", "xml",
                "接口", "函數", "方法", "類", "變量", "數據庫", "服務器",
                "客戶端", "請求", "響應", "配置", "安裝"
            ],
            "icon": "💻"
        }
    }
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def detect_from_filename(self, filename: str) -> Dict[str, float]:
        """
        從文件名檢測領域
        
        Returns:
            Dict[str, float]: 各領域置信度分數
        """
        scores = {}
        filename_lower = filename.lower()
        
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            score = 0
            matched_keywords = []
            
            for keyword in keywords["filename_keywords"]:
                if keyword.lower() in filename_lower:
                    score += 1
                    matched_keywords.append(keyword)
            
            # 正規化分數 (0-1)
            scores[domain] = min(score / 3, 1.0)  # 最多3個匹配詞得滿分
            
            if score > 0:
                self.logger.debug(f"Domain '{domain}': matched {matched_keywords}")
        
        return scores
    
    def detect_from_content(self, content_samples: List[str]) -> Dict[str, float]:
        """
        從內容樣本檢測領域
        
        Args:
            content_samples: 文本樣本列表 (前N段文字)
            
        Returns:
            Dict[str, float]: 各領域置信度分數
        """
        scores = {}
        content_text = " ".join(content_samples).lower()
        
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            score = 0
            matched_count = 0
            
            for keyword in keywords["content_keywords"]:
                count = content_text.count(keyword.lower())
                if count > 0:
                    matched_count += 1
                    score += min(count, 3)  # 每個關鍵詞最多計3次
            
            # 正規化分數
            scores[domain] = min(score / 10, 1.0)  # 10個匹配得滿分
        
        return scores
    
    def detect(self, filename: str, content_samples: List[str] = None) -> Tuple[str, float]:
        """
        綜合檢測領域
        
        Args:
            filename: 文件名
            content_samples: 內容樣本 (可選)
            
        Returns:
            Tuple[str, float]: (領域, 置信度)
        """
        # 文件名檢測 (權重 0.4)
        filename_scores = self.detect_from_filename(filename)
        
        # 內容檢測 (權重 0.6)
        if content_samples:
            content_scores = self.detect_from_content(content_samples)
        else:
            content_scores = {domain: 0 for domain in self.DOMAIN_KEYWORDS}
        
        # 合併分數
        combined_scores = {}
        for domain in self.DOMAIN_KEYWORDS:
            combined_scores[domain] = (
                filename_scores.get(domain, 0) * 0.4 +
                content_scores.get(domain, 0) * 0.6
            )
        
        # 選擇最高分
        if not combined_scores:
            return "general", 0.0
        
        best_domain = max(combined_scores, key=combined_scores.get)
        best_score = combined_scores[best_domain]
        
        # 閾值判斷
        if best_score < 0.2:
            return "general", best_score
        
        self.logger.info(f"Detected domain: {best_domain} (confidence: {best_score:.2f})")
        return best_domain, best_score
    
    def get_domain_info(self, domain: str) -> Dict:
        """獲取領域信息"""
        if domain == "general":
            return {
                "name": "通用领域",
                "name_en": "General",
                "icon": "📋"
            }
        
        info = self.DOMAIN_KEYWORDS.get(domain, {})
        return {
            "name": info.get("name", domain),
            "name_en": domain.capitalize(),
            "icon": info.get("icon", "📄")
        }


class DomainPromptEnhancer:
    """
    領域Prompt增強器
    根據檢測到的領域優化翻譯Prompt
    """
    
    # 領域特定術語表 (可擴展)
    DOMAIN_GLOSSARY = {
        "electronics": {
            "藍牙": "Bluetooth",
            "充電": "charging",
            "電池": "battery",
            "電壓": "voltage",
            "電流": "current",
            "功率": "power",
            "輸入": "input",
            "輸出": "output",
            "規格": "specifications",
            "型號": "model"
        },
        "medical": {
            "患者": "patient",
            "診斷": "diagnosis",
            "治療": "treatment",
            "症狀": "symptom",
            "手術": "surgery",
            "植入": "implant"
        },
        "legal": {
            "甲方": "Party A",
            "乙方": "Party B",
            "條款": "clause",
            "合同": "contract",
            "協議": "agreement",
            "違約": "breach of contract"
        }
    }
    
    def enhance_prompt(self, base_prompt: str, domain: str) -> str:
        """
        增強Prompt
        
        Args:
            base_prompt: 基礎Prompt
            domain: 領域
            
        Returns:
            str: 增強後的Prompt
        """
        glossary = self.DOMAIN_GLOSSARY.get(domain, {})
        
        if not glossary:
            return base_prompt
        
        # 構建術語表提示
        glossary_text = "\n".join([f"  {k} -> {v}" for k, v in list(glossary.items())[:10]])
        
        enhanced = f"""{base_prompt}

Important terminology for this domain:
{glossary_text}

Use these standard terms consistently."""
        
        return enhanced
    
    def post_process(self, text: str, domain: str) -> str:
        """
        後處理 - 確保術語一致性
        
        Args:
            text: 翻譯後的文本
            domain: 領域
            
        Returns:
            str: 處理後的文本
        """
        glossary = self.DOMAIN_GLOSSARY.get(domain, {})
        
        if not glossary:
            return text
        
        # 簡單的術語替換 (可擴展為更複雜的邏輯)
        # 注意: 這裡只替換明確的術語，避免過度替換
        
        return text


# 全局檢測器實例
_detector_instance = None

def get_domain_detector() -> DomainDetector:
    """獲取全局檢測器實例"""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = DomainDetector()
    return _detector_instance


if __name__ == "__main__":
    # 測試
    logging.basicConfig(level=logging.INFO)
    
    detector = DomainDetector()
    
    # 測試文件名檢測
    test_files = [
        "DEP-108 產品規格書.docx",
        "醫療器械註冊合同.pdf",
        "Marketing_Plan_2026.pptx",
        "API_Documentation_v2.docx"
    ]
    
    for filename in test_files:
        domain, confidence = detector.detect(filename)
        info = detector.get_domain_info(domain)
        print(f"{filename} -> {info['icon']} {info['name']} ({confidence:.2f})")
