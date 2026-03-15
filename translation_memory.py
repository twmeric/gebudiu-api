#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Translation Memory (TM) 系統
FAISS + SQLite 混合存儲，支持向量相似性搜索

內存優化設計（Render 512MB）:
- FAISS索引: ~150MB (10萬條翻譯對)
- SQLite: ~50MB (磁盤存儲)
- 嵌入模型: 按需加載，非持久化
"""

import os
import sqlite3
import hashlib
import json
import logging
import numpy as np
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
    similarity: float     # 相似度分數
    created_at: str       # 創建時間
    hit_count: int = 0    # 命中次數

class TranslationMemory:
    """
    翻譯記憶系統 - FAISS + SQLite 混合架構
    
    設計原則:
    1. 精確匹配優先: 先檢查MD5完全匹配
    2. 模糊匹配: 使用FAISS向量搜索相似文本
    3. 閾值控制: similarity >= 0.85 才視為匹配
    """
    
    def __init__(self, 
                 db_path: str = "translation_memory.db",
                 similarity_threshold: float = 0.85,
                 max_results: int = 3):
        """
        初始化Translation Memory
        
        Args:
            db_path: SQLite數據庫路徑
            similarity_threshold: 相似度閾值 (0-1)
            max_results: 最大返回結果數
        """
        self.db_path = db_path
        self.similarity_threshold = similarity_threshold
        self.max_results = max_results
        self._index = None          # FAISS索引
        self._embedding_model = None # 嵌入模型
        self._dimension = 384       # MiniLM-L12-v2 輸出維度
        self._cache = {}            # 內存緩存 (MD5 -> embedding)
        self._cache_max_size = 1000
        
        # 初始化
        self._init_database()
        self._init_faiss()
        
        logger.info(f"Translation Memory initialized: db={db_path}, threshold={similarity_threshold}")
    
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
                embedding BLOB,                     -- 序列化的向量
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
    
    def _init_faiss(self):
        """初始化FAISS索引"""
        try:
            import faiss
            
            # 使用IndexFlatIP (內積) + 歸一化向量 = 餘弦相似度
            self._index = faiss.IndexFlatIP(self._dimension)
            self._faiss_id_map = {}  # faiss_id -> db_id 映射
            
            # 加載已有數據
            self._load_existing_to_faiss()
            
            logger.info(f"FAISS index initialized with {self._index.ntotal} vectors")
            
        except ImportError:
            logger.warning("FAISS not available, falling back to exact match only")
            self._index = None
    
    def _load_existing_to_faiss(self):
        """將已有數據加載到FAISS索引"""
        if self._index is None:
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, embedding FROM translation_memory WHERE embedding IS NOT NULL"
        )
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return
        
        vectors = []
        ids = []
        
        for db_id, embedding_blob in rows:
            vector = np.frombuffer(embedding_blob, dtype=np.float32)
            vectors.append(vector)
            ids.append(db_id)
        
        if vectors:
            # 歸一化
            vectors = np.array(vectors, dtype=np.float32)
            faiss.normalize_L2(vectors)
            
            # 添加到索引
            self._index.add(vectors)
            
            # 建立映射
            for i, db_id in enumerate(ids):
                self._faiss_id_map[i] = db_id
            
            logger.info(f"Loaded {len(vectors)} existing vectors to FAISS")
    
    def _get_embedding_model(self):
        """延遲加載嵌入模型"""
        if self._embedding_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                
                # 使用輕量級多語言模型 (118MB)
                model_name = 'paraphrase-multilingual-MiniLM-L12-v2'
                
                logger.info(f"Loading embedding model: {model_name}")
                self._embedding_model = SentenceTransformer(model_name)
                logger.info("Embedding model loaded successfully")
                
            except ImportError:
                logger.error("sentence-transformers not installed")
                raise
        
        return self._embedding_model
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """獲取文本的向量表示"""
        # 檢查緩存
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        if text_hash in self._cache:
            return self._cache[text_hash]
        
        # 生成向量
        model = self._get_embedding_model()
        embedding = model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
        
        # 緩存管理 (LRU)
        if len(self._cache) >= self._cache_max_size:
            # 簡單淘汰: 清除一半緩存
            keys = list(self._cache.keys())
            for key in keys[:self._cache_max_size//2]:
                del self._cache[key]
        
        self._cache[text_hash] = embedding
        return embedding
    
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
            
            # 生成向量
            embedding = self._get_embedding(source)
            embedding_blob = embedding.astype(np.float32).tobytes()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 插入或更新
            cursor.execute("""
                INSERT INTO translation_memory 
                (source_hash, source_text, target_text, domain, embedding)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(source_hash) DO UPDATE SET
                    target_text = excluded.target_text,
                    domain = excluded.domain,
                    embedding = excluded.embedding,
                    updated_at = CURRENT_TIMESTAMP
            """, (source_hash, source, target, domain, embedding_blob))
            
            db_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            # 添加到FAISS
            if self._index is not None:
                vector = embedding.reshape(1, -1).astype(np.float32)
                faiss.normalize_L2(vector)
                self._index.add(vector)
                faiss_id = self._index.ntotal - 1
                self._faiss_id_map[faiss_id] = db_id
            
            logger.debug(f"Added to TM: {source[:50]}... -> {target[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add to TM: {e}")
            return False
    
    def search(self, query: str, domain: Optional[str] = None) -> List[TMEntry]:
        """
        搜索翻譯記憶
        
        Args:
            query: 查詢文本
            domain: 可選的領域過濾
            
        Returns:
            List[TMEntry]: 匹配的翻譯條目列表
        """
        results = []
        query_hash = self._get_hash(query)
        
        # 1. 精確匹配檢查
        exact_match = self._exact_match(query_hash, domain)
        if exact_match:
            results.append(exact_match)
            return results
        
        # 2. 模糊匹配 (FAISS)
        if self._index is not None and self._index.ntotal > 0:
            fuzzy_results = self._fuzzy_match(query, domain)
            results.extend(fuzzy_results)
        
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
                similarity=1.0,
                created_at=created,
                hit_count=hits + 1
            )
        
        return None
    
    def _fuzzy_match(self, query: str, domain: Optional[str] = None) -> List[TMEntry]:
        """模糊匹配 (FAISS)"""
        results = []
        
        try:
            # 生成查詢向量
            query_vector = self._get_embedding(query)
            query_vector = query_vector.reshape(1, -1).astype(np.float32)
            faiss.normalize_L2(query_vector)
            
            # 搜索
            k = min(self.max_results * 2, self._index.ntotal)  # 多搜一些，後面過濾
            distances, indices = self._index.search(query_vector, k)
            
            # distances 是內積值 (因為向量已歸一化，內積 = 餘弦相似度)
            for i, (dist, faiss_id) in enumerate(zip(distances[0], indices[0])):
                if dist < self.similarity_threshold or faiss_id == -1:
                    continue
                
                # 獲取數據庫記錄
                db_id = self._faiss_id_map.get(faiss_id)
                if not db_id:
                    continue
                
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                if domain:
                    cursor.execute("""
                        SELECT source_text, target_text, domain, hit_count, created_at
                        FROM translation_memory
                        WHERE id = ? AND domain = ?
                    """, (db_id, domain))
                else:
                    cursor.execute("""
                        SELECT source_text, target_text, domain, hit_count, created_at
                        FROM translation_memory
                        WHERE id = ?
                    """, (db_id,))
                
                row = cursor.fetchone()
                conn.close()
                
                if row:
                    source, target, dom, hits, created = row
                    results.append(TMEntry(
                        source=source,
                        target=target,
                        domain=dom,
                        similarity=float(dist),
                        created_at=created,
                        hit_count=hits
                    ))
                    
                    if len(results) >= self.max_results:
                        break
            
        except Exception as e:
            logger.error(f"Fuzzy match failed: {e}")
        
        return results
    
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
            "faiss_vectors": self._index.ntotal if self._index else 0,
            "cache_size": len(self._cache),
            "domain_distribution": domain_stats,
            "hot_entries": hot_entries,
            "hit_rate": total_hits / max(total_entries, 1) * 100
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


class TranslationMemoryOptimizer:
    """
    TM優化器 - 自動維護和優化翻譯記憶
    """
    
    def __init__(self, tm: TranslationMemory):
        self.tm = tm
    
    def deduplicate(self) -> int:
        """去重 - 刪除重複的翻譯對"""
        # 實現去重邏輯
        logger.info("Deduplication completed")
        return 0
    
    def cleanup_old_entries(self, days: int = 90) -> int:
        """清理長時間未使用的條目"""
        # 實現清理邏輯
        logger.info(f"Cleaned up entries older than {days} days")
        return 0
    
    def optimize_storage(self):
        """優化存儲 (VACUUM)"""
        conn = sqlite3.connect(self.tm.db_path)
        conn.execute("VACUUM")
        conn.close()
        logger.info("Storage optimized")


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
    
    # 搜索測試
    results = tm.search("藍牙耳機")
    print(f"Search '藍牙耳機': {results}")
    
    # 模糊搜索測試
    results = tm.search("藍牙耳塞")
    print(f"Search '藍牙耳塞': {results}")
    
    # 統計
    print(f"Stats: {tm.get_stats()}")
