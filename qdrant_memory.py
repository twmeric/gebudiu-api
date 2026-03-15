#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Qdrant 向量搜索 - 方案E實現
提供模糊匹配功能，與SQLite精確匹配形成兩級緩存

注意: 此模塊在 Render 上可能不可用（Python 3.14 構建問題）
只在本地開發環境使用
"""

import os
import logging
import hashlib
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# 檢查依賴可用性
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    logger.warning("qdrant-client not installed, Qdrant TM disabled")

@dataclass
class QdrantEntry:
    """Qdrant搜索結果條目"""
    source: str
    target: str
    similarity: float
    domain: str

class QdrantTranslationMemory:
    """
    Qdrant 向量翻譯記憶
    
    特性:
    - 向量相似性搜索 (餘弦相似度)
    - 支持多領域集合
    - 與SQLite TM形成兩級緩存
    """
    
    def __init__(self, 
                 url: Optional[str] = None,
                 api_key: Optional[str] = None,
                 similarity_threshold: float = 0.85):
        """
        初始化 Qdrant TM
        
        Args:
            url: Qdrant服務URL
            api_key: API密鑰
            similarity_threshold: 相似度閾值
        """
        self.url = url or os.getenv("QDRANT_URL")
        self.api_key = api_key or os.getenv("QDRANT_API_KEY")
        self.similarity_threshold = similarity_threshold
        
        # 延遲初始化客戶端和模型
        self._client = None
        self._embedder = None
        
        if not self.url:
            logger.warning("QDRANT_URL not set, Qdrant TM disabled")
            return
        
        try:
            self._init_client()
            logger.info("QdrantTranslationMemory initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant: {e}")
            self._client = None
    
    def _init_client(self):
        """初始化 Qdrant 客戶端"""
        if not QDRANT_AVAILABLE:
            logger.error("qdrant-client not installed")
            return
            
        try:
            self._client = QdrantClient(
                url=self.url,
                api_key=self.api_key,
                timeout=30
            )
            
            # 確保集合存在
            self._ensure_collections()
            
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant client: {e}")
            self._client = None
    
    def _init_embedder(self):
        """延遲初始化嵌入模型"""
        if self._embedder is None:
            try:
                from sentence_transformers import SentenceTransformer
                
                logger.info("Loading embedding model for Qdrant...")
                self._embedder = SentenceTransformer(
                    'paraphrase-multilingual-MiniLM-L12-v2',
                    cache_folder='/tmp/sentence_transformers'
                )
                logger.info("Embedding model loaded")
                
            except ImportError:
                logger.error("sentence-transformers not installed")
                raise
    
    def _ensure_collections(self):
        """確保所有領域集合存在"""
        if not self._client:
            return
        
        domains = ["general", "electronics", "medical", "legal", "marketing", "industrial", "software"]
        
        for domain in domains:
            collection_name = f"tm_{domain}"
            
            try:
                # 檢查集合是否存在
                self._client.get_collection(collection_name)
                logger.debug(f"Collection {collection_name} exists")
                
            except Exception:
                # 創建集合
                try:
                    from qdrant_client.models import Distance, VectorParams
                    
                    self._client.create_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(
                            size=384,  # MiniLM-L12-v2 輸出維度
                            distance=Distance.COSINE
                        )
                    )
                    logger.info(f"Created collection: {collection_name}")
                    
                except Exception as e:
                    logger.error(f"Failed to create collection {collection_name}: {e}")
    
    def is_available(self) -> bool:
        """檢查 Qdrant 是否可用"""
        return self._client is not None
    
    def add(self, source: str, target: str, domain: str = "general") -> bool:
        """
        添加翻譯對到 Qdrant
        
        Args:
            source: 原文
            target: 譯文
            domain: 領域
            
        Returns:
            bool: 是否成功
        """
        if not self.is_available():
            return False
        
        try:
            # 延遲初始化嵌入模型
            self._init_embedder()
            
            # 生成向量
            vector = self._embedder.encode(source)
            
            # 生成唯一ID
            point_id = hashlib.md5(f"{domain}:{source}".encode()).hexdigest()[:16]
            point_id = int(point_id, 16) % (2**63)  # 轉為正整數
            
            collection_name = f"tm_{domain}"
            
            # 插入或更新
            self._client.upsert(
                collection_name=collection_name,
                points=[{
                    "id": point_id,
                    "vector": vector.tolist(),
                    "payload": {
                        "source": source,
                        "target": target,
                        "domain": domain
                    }
                }]
            )
            
            logger.debug(f"Added to Qdrant: {source[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add to Qdrant: {e}")
            return False
    
    def search(self, query: str, domain: Optional[str] = None, 
               limit: int = 3) -> List[QdrantEntry]:
        """
        向量相似性搜索
        
        Args:
            query: 查詢文本
            domain: 領域 (默認搜索所有領域)
            limit: 返回結果數
            
        Returns:
            List[QdrantEntry]: 匹配結果列表
        """
        if not self.is_available():
            return []
        
        try:
            # 延遲初始化嵌入模型
            self._init_embedder()
            
            # 生成查詢向量
            query_vector = self._embedder.encode(query)
            
            results = []
            
            if domain:
                # 搜索指定領域
                results = self._search_collection(domain, query_vector, limit)
            else:
                # 搜索所有領域
                domains = ["general", "electronics", "medical", "legal", "marketing", "industrial", "software"]
                for d in domains:
                    domain_results = self._search_collection(d, query_vector, limit)
                    results.extend(domain_results)
                
                # 按相似度排序
                results.sort(key=lambda x: x.similarity, reverse=True)
                results = results[:limit]
            
            return results
            
        except Exception as e:
            logger.error(f"Qdrant search failed: {e}")
            return []
    
    def _search_collection(self, domain: str, query_vector, limit: int) -> List[QdrantEntry]:
        """搜索單個集合"""
        collection_name = f"tm_{domain}"
        
        try:
            search_results = self._client.search(
                collection_name=collection_name,
                query_vector=query_vector.tolist(),
                limit=limit,
                score_threshold=self.similarity_threshold
            )
            
            return [
                QdrantEntry(
                    source=hit.payload["source"],
                    target=hit.payload["target"],
                    similarity=hit.score,
                    domain=domain
                )
                for hit in search_results
            ]
            
        except Exception as e:
            logger.debug(f"Search failed for {collection_name}: {e}")
            return []
    
    def get_stats(self) -> Dict:
        """獲取統計信息"""
        if not self.is_available():
            return {
                "status": "disabled",
                "reason": "QDRANT_URL not configured"
            }
        
        try:
            total_points = 0
            collections_info = {}
            
            domains = ["general", "electronics", "medical", "legal", "marketing", "industrial", "software"]
            
            for domain in domains:
                collection_name = f"tm_{domain}"
                try:
                    info = self._client.get_collection(collection_name)
                    count = info.points_count
                    total_points += count
                    collections_info[domain] = count
                except:
                    collections_info[domain] = 0
            
            return {
                "status": "active",
                "url": self.url.replace(self.url.split('/')[-1], '***') if self.url else None,
                "similarity_threshold": self.similarity_threshold,
                "total_points": total_points,
                "collections": collections_info
            }
            
        except Exception as e:
            logger.error(f"Failed to get Qdrant stats: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def batch_add(self, entries: List[Tuple[str, str, str]]) -> int:
        """
        批量添加
        
        Args:
            entries: [(source, target, domain), ...]
            
        Returns:
            int: 成功數
        """
        if not self.is_available():
            return 0
        
        success_count = 0
        
        for source, target, domain in entries:
            if self.add(source, target, domain):
                success_count += 1
        
        return success_count


# 全局實例
_qdrant_tm_instance = None

def get_qdrant_translation_memory() -> Optional[QdrantTranslationMemory]:
    """獲取全局 Qdrant TM 實例"""
    global _qdrant_tm_instance
    if _qdrant_tm_instance is None:
        _qdrant_tm_instance = QdrantTranslationMemory()
    return _qdrant_tm_instance


if __name__ == "__main__":
    # 測試
    logging.basicConfig(level=logging.INFO)
    
    # 需要設置環境變量才能測試
    if os.getenv("QDRANT_URL"):
        qtm = QdrantTranslationMemory()
        
        if qtm.is_available():
            print("✅ Qdrant TM initialized successfully")
            
            # 添加測試數據
            qtm.add("藍牙耳機", "Bluetooth Earphones", "electronics")
            qtm.add("產品規格書", "Product Specification", "general")
            
            # 搜索測試
            results = qtm.search("藍牙耳機", "electronics")
            print(f"\nSearch results: {len(results)}")
            for r in results:
                print(f"  {r.source} -> {r.target} (sim: {r.similarity:.3f})")
            
            # 統計
            print(f"\nStats: {qtm.get_stats()}")
        else:
            print("❌ Qdrant not available")
    else:
        print("⚠️ Set QDRANT_URL environment variable to test")
