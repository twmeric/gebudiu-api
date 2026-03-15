#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
術語表管理系統
支持用戶自定義術語表和系統預設術語庫
"""

import os
import sqlite3
import csv
import json
import re
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
from io import StringIO

logger = logging.getLogger(__name__)

@dataclass
class TermEntry:
    """術語條目"""
    source: str           # 原文
    target: str           # 譯文
    domain: str           # 所屬領域
    category: str         # 類別 (產品/技術/標準)
    priority: int         # 優先級 (1-10, 10最高)
    created_at: str       # 創建時間
    updated_at: str       # 更新時間
    usage_count: int      # 使用次數

class TerminologyManager:
    """
    術語表管理器
    
    功能:
    1. 用戶自定義術語表 (CSV上傳)
    2. 系統預設行業術語庫
    3. 翻譯前術語預處理 (標記保護)
    4. 翻譯後術語校驗 (一致性檢查)
    5. 術語使用統計
    """
    
    # 系統預設術語庫
    DEFAULT_GLOSSARIES = {
        "electronics": {
            "藍牙": "Bluetooth",
            "藍牙耳機": "Bluetooth Earphones",
            "充電": "Charging",
            "充電器": "Charger",
            "電池": "Battery",
            "電源": "Power Supply",
            "電壓": "Voltage",
            "電流": "Current",
            "功率": "Power",
            "輸入": "Input",
            "輸出": "Output",
            "規格": "Specifications",
            "型號": "Model",
            "尺寸": "Dimensions",
            "重量": "Weight",
            "材質": "Material",
            "顏色": "Color",
            "無線": "Wireless",
            "有線": "Wired",
            "USB": "USB",
            "Type-C": "Type-C",
            "LED": "LED",
            "顯示屏": "Display Screen",
            "按鈕": "Button",
            "開關": "Switch",
            "指示燈": "Indicator Light",
            "保護": "Protection",
            "過壓保護": "Overvoltage Protection",
            "過流保護": "Overcurrent Protection",
            "短路保護": "Short Circuit Protection",
            "溫度保護": "Temperature Protection"
        },
        "medical": {
            "患者": "Patient",
            "診斷": "Diagnosis",
            "治療": "Treatment",
            "症狀": "Symptom",
            "疾病": "Disease",
            "臨床": "Clinical",
            "醫療器械": "Medical Device",
            "滅菌": "Sterilization",
            "消毒": "Disinfection",
            "生物相容性": "Biocompatibility",
            "手術": "Surgery",
            "手術室": "Operating Room",
            "植入": "Implant",
            "植入物": "Implantable Device",
            "導管": "Catheter",
            "傷口": "Wound",
            "止血": "Hemostasis",
            "縫合": "Suture",
            "麻醉": "Anesthesia",
            "劑量": "Dosage",
            "處方": "Prescription",
            "不良反應": "Adverse Reaction",
            "副作用": "Side Effect",
            "禁忌": "Contraindication",
            "警告": "Warning",
            "注意事項": "Precautions"
        },
        "legal": {
            "甲方": "Party A",
            "乙方": "Party B",
            "丙方": "Party C",
            "合同": "Contract",
            "協議": "Agreement",
            "條款": "Clause",
            "條文": "Article",
            "附件": "Appendix",
            "補充協議": "Supplementary Agreement",
            "違約": "Breach of Contract",
            "違約金": "Liquidated Damages",
            "賠償": "Compensation",
            "損失": "Loss",
            "責任": "Liability",
            "免除責任": "Exemption from Liability",
            "限制責任": "Limitation of Liability",
            "不可抗力": "Force Majeure",
            "爭議": "Dispute",
            "仲裁": "Arbitration",
            "訴訟": "Litigation",
            "管轄": "Jurisdiction",
            "適用法律": "Governing Law",
            "生效": "Effective",
            "終止": "Termination",
            "解除": "Rescission",
            "修訂": "Amendment",
            "修改": "Modification"
        },
        "industrial": {
            "機器": "Machine",
            "設備": "Equipment",
            "機械": "Machinery",
            "製造": "Manufacturing",
            "生產": "Production",
            "工廠": "Factory",
            "車間": "Workshop",
            "裝配": "Assembly",
            "裝配線": "Assembly Line",
            "自動化": "Automation",
            "半自動": "Semi-automatic",
            "手動": "Manual",
            "操作": "Operation",
            "維護": "Maintenance",
            "保養": "Servicing",
            "檢修": "Inspection and Repair",
            "校準": "Calibration",
            "精度": "Accuracy",
            "公差": "Tolerance",
            "規格": "Specification",
            "標準": "Standard",
            "ISO": "ISO",
            "質量": "Quality",
            "質量控制": "Quality Control",
            "質量管理": "Quality Management",
            "檢驗": "Inspection",
            "測試": "Testing",
            "認證": "Certification"
        }
    }
    
    def __init__(self, db_path: str = "terminology.db"):
        """
        初始化術語表管理器
        
        Args:
            db_path: SQLite數據庫路徑
        """
        self.db_path = db_path
        self._init_database()
        self._load_default_glossaries()
        
        logger.info(f"TerminologyManager initialized: {db_path}")
    
    def _init_database(self):
        """初始化數據庫"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 術語表主表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS terminology (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,              -- 原文
                target TEXT NOT NULL,              -- 譯文
                domain TEXT DEFAULT 'general',     -- 領域
                category TEXT DEFAULT 'general',   -- 類別
                priority INTEGER DEFAULT 5,        -- 優先級 1-10
                is_system BOOLEAN DEFAULT 0,       -- 是否系統預設
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                usage_count INTEGER DEFAULT 0,
                UNIQUE(source, domain)
            )
        """)
        
        # 索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_terminology_source 
            ON terminology(source)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_terminology_domain 
            ON terminology(domain)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_terminology_priority 
            ON terminology(priority DESC)
        """)
        
        # 用戶自定義術語表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_glossaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                domain TEXT DEFAULT 'general',
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        """)
        
        # 統計表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS terminology_stats (
                id INTEGER PRIMARY KEY,
                total_terms INTEGER DEFAULT 0,
                user_terms INTEGER DEFAULT 0,
                system_terms INTEGER DEFAULT 0,
                total_usage INTEGER DEFAULT 0
            )
        """)
        
        cursor.execute("""
            INSERT OR IGNORE INTO terminology_stats (id) VALUES (1)
        """)
        
        conn.commit()
        conn.close()
        logger.info("Terminology database initialized")
    
    def _load_default_glossaries(self):
        """加載系統預設術語庫"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 檢查是否已加載
        cursor.execute("SELECT COUNT(*) FROM terminology WHERE is_system = 1")
        count = cursor.fetchone()[0]
        
        if count > 0:
            logger.info(f"System glossaries already loaded: {count} terms")
            conn.close()
            return
        
        # 加載預設術語
        total = 0
        for domain, glossary in self.DEFAULT_GLOSSARIES.items():
            for source, target in glossary.items():
                cursor.execute("""
                    INSERT OR IGNORE INTO terminology 
                    (source, target, domain, category, priority, is_system)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (source, target, domain, 'standard', 8, True))
                total += 1
        
        conn.commit()
        conn.close()
        
        logger.info(f"Loaded {total} system default terms")
    
    def add_term(self, source: str, target: str, domain: str = "general",
                 category: str = "custom", priority: int = 5) -> bool:
        """
        添加術語
        
        Args:
            source: 原文
            target: 譯文
            domain: 領域
            category: 類別
            priority: 優先級 (1-10)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO terminology 
                (source, target, domain, category, priority, is_system)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(source, domain) DO UPDATE SET
                    target = excluded.target,
                    category = excluded.category,
                    priority = excluded.priority,
                    updated_at = CURRENT_TIMESTAMP
            """, (source.strip(), target.strip(), domain, category, priority, False))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Added term: {source} -> {target} ({domain})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add term: {e}")
            return False
    
    def import_from_csv(self, csv_content: str, domain: str = "general") -> Tuple[int, int]:
        """
        從 CSV 導入術語表
        
        CSV格式: source,target,category(可選),priority(可選)
        
        Args:
            csv_content: CSV內容字符串
            domain: 領域
            
        Returns:
            (成功數, 失敗數)
        """
        success = 0
        failed = 0
        
        try:
            f = StringIO(csv_content)
            reader = csv.reader(f)
            
            for row in reader:
                if len(row) < 2:
                    failed += 1
                    continue
                
                source = row[0].strip()
                target = row[1].strip()
                category = row[2].strip() if len(row) > 2 else "custom"
                priority = int(row[3]) if len(row) > 3 and row[3].isdigit() else 5
                
                if self.add_term(source, target, domain, category, priority):
                    success += 1
                else:
                    failed += 1
            
            logger.info(f"Imported {success} terms, {failed} failed")
            return success, failed
            
        except Exception as e:
            logger.error(f"CSV import failed: {e}")
            return success, failed
    
    def export_to_csv(self, domain: Optional[str] = None) -> str:
        """
        導出術語表到 CSV
        
        Args:
            domain: 可選的領域過濾
            
        Returns:
            CSV 內容字符串
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if domain:
            cursor.execute("""
                SELECT source, target, category, priority, is_system
                FROM terminology
                WHERE domain = ?
                ORDER BY priority DESC, source
            """, (domain,))
        else:
            cursor.execute("""
                SELECT source, target, category, priority, is_system
                FROM terminology
                ORDER BY domain, priority DESC, source
            """)
        
        rows = cursor.fetchall()
        conn.close()
        
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["source", "target", "category", "priority", "is_system"])
        
        for row in rows:
            writer.writerow(row)
        
        return output.getvalue()
    
    def get_terms(self, domain: Optional[str] = None, 
                  category: Optional[str] = None,
                  limit: int = 1000) -> List[TermEntry]:
        """
        獲取術語列表
        
        Args:
            domain: 領域過濾
            category: 類別過濾
            limit: 返回數量限制
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = """
            SELECT source, target, domain, category, priority, 
                   created_at, updated_at, usage_count
            FROM terminology
            WHERE 1=1
        """
        params = []
        
        if domain:
            query += " AND domain = ?"
            params.append(domain)
        
        if category:
            query += " AND category = ?"
            params.append(category)
        
        query += " ORDER BY priority DESC, source LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [
            TermEntry(
                source=row[0],
                target=row[1],
                domain=row[2],
                category=row[3],
                priority=row[4],
                created_at=row[5],
                updated_at=row[6],
                usage_count=row[7]
            )
            for row in rows
        ]
    
    def search_terms(self, query: str, domain: Optional[str] = None) -> List[TermEntry]:
        """搜索術語"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if domain:
            cursor.execute("""
                SELECT source, target, domain, category, priority,
                       created_at, updated_at, usage_count
                FROM terminology
                WHERE (source LIKE ? OR target LIKE ?) AND domain = ?
                ORDER BY priority DESC, source
            """, (f"%{query}%", f"%{query}%", domain))
        else:
            cursor.execute("""
                SELECT source, target, domain, category, priority,
                       created_at, updated_at, usage_count
                FROM terminology
                WHERE source LIKE ? OR target LIKE ?
                ORDER BY priority DESC, source
            """, (f"%{query}%", f"%{query}%"))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            TermEntry(
                source=row[0],
                target=row[1],
                domain=row[2],
                category=row[3],
                priority=row[4],
                created_at=row[5],
                updated_at=row[6],
                usage_count=row[7]
            )
            for row in rows
        ]
    
    def get_preprocessing_map(self, domain: Optional[str] = None) -> Dict[str, str]:
        """
        獲取預處理映射表
        
        用於翻譯前的術語標記保護
        
        Returns:
            {原文: 標記後文本}
        """
        terms = self.get_terms(domain, limit=5000)
        
        # 按長度降序排序，避免部分匹配
        terms.sort(key=lambda t: len(t.source), reverse=True)
        
        mapping = {}
        for term in terms:
            # 創建唯一標記
            marker = f"__TERM_{hash(term.source) % 1000000:06d}__"
            mapping[term.source] = marker
        
        return mapping
    
    def preprocess_text(self, text: str, domain: Optional[str] = None) -> Tuple[str, Dict[str, str]]:
        """
        翻譯前預處理 - 標記保護術語
        
        Args:
            text: 原文
            domain: 領域
            
        Returns:
            (預處理後文本, 標記映射表)
        """
        mapping = self.get_preprocessing_map(domain)
        marker_to_term = {}
        
        processed = text
        for source, marker in mapping.items():
            if source in processed:
                processed = processed.replace(source, marker)
                marker_to_term[marker] = source
        
        return processed, marker_to_term
    
    def postprocess_text(self, text: str, marker_map: Dict[str, str], 
                         domain: Optional[str] = None) -> str:
        """
        翻譯後處理 - 還原術語
        
        Args:
            text: 翻譯後文本 (含標記)
            marker_map: 標記到原文的映射
            domain: 領域
            
        Returns:
            處理後文本
        """
        # 獲取術語映射
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if domain:
            cursor.execute("""
                SELECT source, target FROM terminology
                WHERE domain = ?
            """, (domain,))
        else:
            cursor.execute("SELECT source, target FROM terminology")
        
        term_dict = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        
        # 替換標記為譯文
        processed = text
        for marker, source in marker_map.items():
            if marker in processed:
                target = term_dict.get(source, source)
                processed = processed.replace(marker, target)
                
                # 更新使用統計
                self._increment_usage(source)
        
        return processed
    
    def _increment_usage(self, source: str):
        """增加術語使用計數"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE terminology
                SET usage_count = usage_count + 1
                WHERE source = ?
            """, (source,))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to increment usage: {e}")
    
    def check_consistency(self, source_text: str, target_text: str,
                          domain: Optional[str] = None) -> List[Dict]:
        """
        檢查術語一致性
        
        檢查原文中出現的術語是否在譯文中正確翻譯
        
        Args:
            source_text: 原文
            target_text: 譯文
            domain: 領域
            
        Returns:
            不一致列表
        """
        inconsistencies = []
        
        # 獲取該領域術語
        terms = self.get_terms(domain)
        term_dict = {t.source: t.target for t in terms}
        
        for source, target in term_dict.items():
            source_count = source_text.count(source)
            target_count = target_text.count(target)
            
            if source_count > 0 and target_count == 0:
                # 術語丟失
                inconsistencies.append({
                    "type": "missing",
                    "source": source,
                    "expected_target": target,
                    "source_count": source_count,
                    "target_count": target_count
                })
            elif source_count > 0 and target_count != source_count:
                # 數量不匹配
                inconsistencies.append({
                    "type": "mismatch",
                    "source": source,
                    "expected_target": target,
                    "source_count": source_count,
                    "target_count": target_count
                })
        
        return inconsistencies
    
    def get_stats(self) -> Dict:
        """獲取統計信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 總術語數
        cursor.execute("SELECT COUNT(*) FROM terminology")
        total = cursor.fetchone()[0]
        
        # 系統/用戶術語數
        cursor.execute("""
            SELECT is_system, COUNT(*) 
            FROM terminology 
            GROUP BY is_system
        """)
        counts = cursor.fetchall()
        system_count = next((c[1] for c in counts if c[0]), 0)
        user_count = next((c[1] for c in counts if not c[0]), 0)
        
        # 各領域分布
        cursor.execute("""
            SELECT domain, COUNT(*) 
            FROM terminology 
            GROUP BY domain
            ORDER BY COUNT(*) DESC
        """)
        domain_stats = {row[0]: row[1] for row in cursor.fetchall()}
        
        # 熱門術語
        cursor.execute("""
            SELECT source, target, usage_count
            FROM terminology
            ORDER BY usage_count DESC
            LIMIT 10
        """)
        hot_terms = [
            {"source": row[0], "target": row[1], "usage": row[2]}
            for row in cursor.fetchall()
        ]
        
        conn.close()
        
        return {
            "total_terms": total,
            "system_terms": system_count,
            "user_terms": user_count,
            "domain_distribution": domain_stats,
            "hot_terms": hot_terms
        }
    
    def delete_term(self, source: str, domain: str) -> bool:
        """刪除術語"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM terminology
                WHERE source = ? AND domain = ? AND is_system = 0
            """, (source, domain))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Failed to delete term: {e}")
            return False


# 全局實例
_terminology_manager = None

def get_terminology_manager() -> TerminologyManager:
    """獲取全局術語管理器"""
    global _terminology_manager
    if _terminology_manager is None:
        _terminology_manager = TerminologyManager()
    return _terminology_manager


if __name__ == "__main__":
    # 測試
    logging.basicConfig(level=logging.INFO)
    
    tm = TerminologyManager("test_terminology.db")
    
    # 測試添加術語
    tm.add_term("測試術語", "Test Term", "general", "custom", 9)
    
    # 測試獲取
    terms = tm.get_terms("electronics", limit=5)
    print(f"\nElectronics terms (top 5):")
    for t in terms:
        print(f"  {t.source} -> {t.target}")
    
    # 測試統計
    stats = tm.get_stats()
    print(f"\nStats:")
    print(f"  Total: {stats['total_terms']}")
    print(f"  System: {stats['system_terms']}")
    print(f"  User: {stats['user_terms']}")
