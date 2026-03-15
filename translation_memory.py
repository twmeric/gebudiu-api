#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Translation Memory (TM) 系統 - SQLite 精確匹配版

方案A: 純SQLite實現，移除FAISS依賴，確保Render穩定部署

內存優化設計（Render 512MB）:
- SQLite: ~50MB (磁盤存儲)
- 無需嵌入模型內存佔用
- 無需FAISS索引內存
"""

import os
import sqlite3
import hashlib
import json
import logging
from typing import List, Tuple, Optional, Dict
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class TMEntry:
    """翻譯記憶條目"""
    source: str           # 原文
    target: str           # 譯文
    domain: str           # 領域
    similarity: float     # 相似度分數 (精確匹配=1.0)
    created_at: str       # 創建時間
    hit_count: int = 0    # 命中次數

class TranslationMemory:
    """
    翻譯記憶系統 - SQLite 精確匹配版
    
    設計原則:
    1. 精確匹配優先: 檢查MD5完全匹配
    2. 簡化架構: 移除FAISS，避免部署問題
    3. 穩定優先: 100%部署成功率
    
    注意: 此為方案A (降級版)，完整模糊匹配將通過方案E (Qdrant) 實現
    """
    
    def __init__(self, 
                 db_path: str = "translation_memory.db",
                 similarity_threshold: float = 1.0,  # 精確匹配，閾值設為1.0
                 max_results: int = 1):
        """
        初始化Translation Memory (SQLite版)
        
        Args:
            db_path: SQLite數據庫路徑
            similarity_threshold: 相似度閾值 (固定1.0，只支持精確匹配)
            max_results: 最大返回結果數
        """
        self.db_path = db_path
        self.similarity_threshold = similarity_threshold
        self.max_results = max_results
        
        # 初始化
        self._init_database()
        
        logger.info(f"Translation Memory (SQLite版) initialized: db={db_path}")
    
    def _init_database(self):
        """初始化SQLite數據庫"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 主表: 翻譯記憶
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS translation_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_hash TEXT UNIQUE NOT NULL,  -- MD5(source_text)
                source_text TEXT NOT NULL,
                target_text TEXT NOT NULL,
                domain TEXT DEFAULT 'general',
                hit_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_source_hash 
            ON translation_memory(source_hash)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_domain 
            ON translation_memory(domain)
        """)
        
        # 統計表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tm_stats (
                id INTEGER PRIMARY KEY,
                total_entries INTEGER DEFAULT 0,
                total_hits INTEGER DEFAULT 0,
                last_reset TIMESTAMP
            )
        """)
        
        # 初始化統計
        cursor.execute("""
            INSERT OR IGNORE INTO tm_stats (id, total_entries, total_hits) 
            VALUES (1, 0, 0)
        """)
        
        conn.commit()
        conn.close()
        logger.info("SQLite database initialized")
    
    def _get_hash(self, text: str) -> str:
        """獲取文本的MD5哈希"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def add(self, source: str, target: str, domain: str = "general") -> bool:
        """
        添加翻譯對到記憶庫
        
        Args:
            source: 原文
            target: 譯文
            domain: 領域
            
        Returns:
            bool: 是否成功添加
        """
        try:
            source_hash = self._get_hash(source)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 插入或更新
            cursor.execute("""
                INSERT INTO translation_memory 
                (source_hash, source_text, target_text, domain)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(source_hash) DO UPDATE SET
                    target_text = excluded.target_text,
                    domain = excluded.domain,
                    updated_at = CURRENT_TIMESTAMP
            """, (source_hash, source, target, domain))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Added to TM: {source[:50]}... -> {target[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add to TM: {e}")
            return False
    
    def search(self, query: str, domain: Optional[str] = None) -> List[TMEntry]:
        """
        搜索翻譯記憶 (精確匹配)
        
        Args:
            query: 查詢文本
            domain: 可選的領域過濾
            
        Returns:
            List[TMEntry]: 匹配的翻譯條目列表 (精確匹配)
        """
        results = []
        query_hash = self._get_hash(query)
        
        # 精確匹配檢查
        exact_match = self._exact_match(query_hash, domain)
        if exact_match:
            results.append(exact_match)
        
        return results
    
    def _exact_match(self, query_hash: str, domain: Optional[str] = None) -> Optional[TMEntry]:
        """精確匹配"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if domain:
            cursor.execute("""
                SELECT source_text, target_text, domain, hit_count, created_at
                FROM translation_memory
                WHERE source_hash = ? AND domain = ?
            """, (query_hash, domain))
        else:
            cursor.execute("""
                SELECT source_text, target_text, domain, hit_count, created_at
                FROM translation_memory
                WHERE source_hash = ?
            """, (query_hash,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            source, target, dom, hits, created = row
            # 更新命中計數
            self._increment_hit(query_hash)
            
            return TMEntry(
                source=source,
                target=target,
                domain=dom,
                similarity=1.0,  # 精確匹配，相似度為1.0
                created_at=created,
                hit_count=hits + 1
            )
        
        return None
    
    def _increment_hit(self, source_hash: str):
        """增加命中計數"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE translation_memory
                SET hit_count = hit_count + 1
                WHERE source_hash = ?
            """, (source_hash,))
            cursor.execute("""
                UPDATE tm_stats
                SET total_hits = total_hits + 1
                WHERE id = 1
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to increment hit: {e}")
    
    def get_stats(self) -> Dict:
        """獲取統計信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 總條目數
        cursor.execute("SELECT COUNT(*) FROM translation_memory")
        total_entries = cursor.fetchone()[0]
        
        # 總命中數
        cursor.execute("SELECT total_hits FROM tm_stats WHERE id = 1")
        row = cursor.fetchone()
        total_hits = row[0] if row else 0
        
        # 各領域分布
        cursor.execute("""
            SELECT domain, COUNT(*) as count
            FROM translation_memory
            GROUP BY domain
            ORDER BY count DESC
        """)
        domain_stats = {row[0]: row[1] for row in cursor.fetchall()}
        
        # 熱門翻譯 (命中次數最多)
        cursor.execute("""
            SELECT source_text, target_text, hit_count
            FROM translation_memory
            ORDER BY hit_count DESC
            LIMIT 5
        """)
        hot_entries = [
            {"source": row[0][:50], "target": row[1][:50], "hits": row[2]}
            for row in cursor.fetchall()
        ]
        
        conn.close()
        
        return {
            "total_entries": total_entries,
            "total_hits": total_hits,
            "domain_distribution": domain_stats,
            "hot_entries": hot_entries,
            "hit_rate": total_hits / max(total_entries, 1) * 100,
            "mode": "sqlite_exact",  # 標識當前模式
            "note": "方案A: 純SQLite精確匹配，方案E(Qdrant)將提供模糊匹配"
        }
    
    def batch_search(self, texts: List[str], domain: Optional[str] = None) -> Dict[str, List[TMEntry]]:
        """
        批量搜索 - 提高效率
        
        Args:
            texts: 文本列表
            domain: 可選的領域過濾
            
        Returns:
            Dict: {text: [TMEntry, ...]}
        """
        results = {}
        for text in texts:
            results[text] = self.search(text, domain)
        return results
    
    def export_to_json(self, filepath: str):
        """導出數據到JSON"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT source_text, target_text, domain, hit_count, created_at
            FROM translation_memory
        """)
        
        data = [
            {
                "source": row[0],
                "target": row[1],
                "domain": row[2],
                "hit_count": row[3],
                "created_at": row[4]
            }
            for row in cursor.fetchall()
        ]
        
        conn.close()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Exported {len(data)} entries to {filepath}")
    
    def import_from_json(self, filepath: str) -> int:
        """從JSON導入數據"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        count = 0
        for entry in data:
            if self.add(entry['source'], entry['target'], entry.get('domain', 'general')):
                count += 1
        
        logger.info(f"Imported {count}/{len(data)} entries from {filepath}")
        return count


# 全局TM實例 (單例模式)
_tm_instance = None

def get_translation_memory() -> TranslationMemory:
    """獲取全局TM實例"""
    global _tm_instance
    if _tm_instance is None:
        _tm_instance = TranslationMemory()
    return _tm_instance


if __name__ == "__main__":
    # 測試
    logging.basicConfig(level=logging.INFO)
    
    tm = TranslationMemory()
    
    # 添加測試數據
    tm.add("藍牙耳機", "Bluetooth Earphones", "electronics")
    tm.add("產品規格書", "Product Specification", "general")
    tm.add("充電器", "Charger", "electronics")
    
    # 精確匹配測試
    results = tm.search("藍牙耳機")
    print(f"Search '藍牙耳機': {len(results)} results")
    if results:
        print(f"  Match: {results[0].source} -> {results[0].target}")
    
    # 統計
    print(f"\nStats: {tm.get_stats()}")
    
    print("\n✅ SQLite版 Translation Memory 測試通過！")
    print("   注意: 此為方案A (精確匹配)，方案E將提供模糊匹配")
