#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Qdrant 初始化腳本
創建集合、遷移SQLite數據到Qdrant
"""

import os
import sys
import logging
import sqlite3
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_qdrant_collections(url: Optional[str] = None, api_key: Optional[str] = None):
    """
    設置 Qdrant 集合
    
    Args:
        url: Qdrant URL
        api_key: API Key
    """
    url = url or os.getenv("QDRANT_URL")
    api_key = api_key or os.getenv("QDRANT_API_KEY")
    
    if not url:
        logger.error("QDRANT_URL not set")
        return False
    
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams
        
        client = QdrantClient(url=url, api_key=api_key)
        
        # 創建所有領域集合
        domains = ["general", "electronics", "medical", "legal", "marketing", "industrial", "software"]
        
        for domain in domains:
            collection_name = f"tm_{domain}"
            
            try:
                # 檢查是否已存在
                client.get_collection(collection_name)
                logger.info(f"Collection {collection_name} already exists")
                
            except Exception:
                # 創建新集合
                client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=384,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created collection: {collection_name}")
        
        logger.info("✅ Qdrant collections setup complete")
        return True
        
    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        return False
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        return False

def migrate_sqlite_to_qdrant(
    sqlite_path: str = "translation_memory.db",
    qdrant_url: Optional[str] = None,
    api_key: Optional[str] = None
):
    """
    將 SQLite 數據遷移到 Qdrant
    
    Args:
        sqlite_path: SQLite數據庫路徑
        qdrant_url: Qdrant URL
        api_key: API Key
    """
    qdrant_url = qdrant_url or os.getenv("QDRANT_URL")
    api_key = api_key or os.getenv("QDRANT_API_KEY")
    
    if not qdrant_url:
        logger.error("QDRANT_URL not set")
        return False
    
    if not os.path.exists(sqlite_path):
        logger.warning(f"SQLite database not found: {sqlite_path}")
        return False
    
    try:
        from qdrant_memory import QdrantTranslationMemory
        
        # 初始化 Qdrant TM
        qtm = QdrantTranslationMemory(qdrant_url, api_key)
        
        if not qtm.is_available():
            logger.error("Qdrant not available")
            return False
        
        # 讀取 SQLite 數據
        conn = sqlite3.connect(sqlite_path)
        cursor = conn.cursor()
        cursor.execute("SELECT source_text, target_text, domain FROM translation_memory")
        rows = cursor.fetchall()
        conn.close()
        
        logger.info(f"Found {len(rows)} entries in SQLite")
        
        # 批量添加到 Qdrant
        success = 0
        failed = 0
        
        for i, (source, target, domain) in enumerate(rows):
            if qtm.add(source, target, domain):
                success += 1
            else:
                failed += 1
            
            if (i + 1) % 100 == 0:
                logger.info(f"Migrated {i + 1}/{len(rows)} entries...")
        
        logger.info(f"✅ Migration complete: {success} success, {failed} failed")
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_qdrant_status(url: Optional[str] = None, api_key: Optional[str] = None):
    """檢查 Qdrant 狀態"""
    url = url or os.getenv("QDRANT_URL")
    api_key = api_key or os.getenv("QDRANT_API_KEY")
    
    if not url:
        print("❌ QDRANT_URL not set")
        return False
    
    try:
        from qdrant_client import QdrantClient
        
        client = QdrantClient(url=url, api_key=api_key)
        
        # 獲取集合列表
        collections = client.get_collections()
        
        print(f"✅ Qdrant connection successful")
        print(f"   URL: {url.replace(url.split('/')[-1], '***')}")
        print(f"\nCollections:")
        
        for collection in collections.collections:
            info = client.get_collection(collection.name)
            print(f"   - {collection.name}: {info.points_count} points")
        
        return True
        
    except Exception as e:
        print(f"❌ Qdrant connection failed: {e}")
        return False

def main():
    """主函數"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Qdrant setup and migration tool")
    parser.add_argument("command", choices=["setup", "migrate", "status", "all"],
                       help="Command to execute")
    parser.add_argument("--url", help="Qdrant URL")
    parser.add_argument("--api-key", help="Qdrant API Key")
    parser.add_argument("--sqlite", default="translation_memory.db",
                       help="SQLite database path")
    
    args = parser.parse_args()
    
    if args.command == "setup":
        success = setup_qdrant_collections(args.url, args.api_key)
        sys.exit(0 if success else 1)
    
    elif args.command == "migrate":
        success = migrate_sqlite_to_qdrant(args.sqlite, args.url, args.api_key)
        sys.exit(0 if success else 1)
    
    elif args.command == "status":
        success = check_qdrant_status(args.url, args.api_key)
        sys.exit(0 if success else 1)
    
    elif args.command == "all":
        print("=== Step 1: Setup collections ===")
        if not setup_qdrant_collections(args.url, args.api_key):
            sys.exit(1)
        
        print("\n=== Step 2: Migrate data ===")
        migrate_sqlite_to_qdrant(args.sqlite, args.url, args.api_key)
        
        print("\n=== Step 3: Check status ===")
        check_qdrant_status(args.url, args.api_key)
        
        print("\n✅ All steps completed!")

if __name__ == "__main__":
    main()
