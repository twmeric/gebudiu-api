# 方案E: Qdrant 外部向量服務集成計劃

> 狀態: 📋 規劃中  
> 預計實施: 1-2 週後  
> 目標: 恢復模糊匹配功能

---

## 🎯 目標

在保留方案A (SQLite精確匹配) 的基礎上，通過 **Qdrant Cloud** 外部服務恢復模糊匹配功能。

---

## 🏗️ 架構設計

```
┌─────────────────────────────────────────────────────────┐
│                    Render Web Service                    │
│                    (Flask API + SQLite TM)              │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  翻譯請求                                                 │
│       ↓                                                  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  1. SQLite 精確匹配                                │  │
│  │     - 本地查詢，速度最快                           │  │
│  │     - 如果命中，直接返回                           │  │
│  └──────────────────────────────────────────────────┘  │
│       ↓ (未命中)                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  2. Qdrant 模糊匹配                                │  │
│  │     - 向量相似性搜索                               │  │
│  │     - 延遲 ~50-100ms                              │  │
│  └──────────────────────────────────────────────────┘  │
│       ↓ (仍未命中)                                       │
│  ┌──────────────────────────────────────────────────┐  │
│  │  3. DeepSeek API 翻譯                              │  │
│  │     - 保存結果到 SQLite + Qdrant                   │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                    Qdrant Cloud                          │
│                    (免費版 / 付費版)                      │
├─────────────────────────────────────────────────────────┤
│  - 向量存儲 (384維)                                      │
│  - 相似性搜索 (餘弦相似度)                                │
│  - 預計存儲: 10萬條翻譯對                                  │
│  - 免費額度: 1GB 存儲 + 10萬請求/月                        │
└─────────────────────────────────────────────────────────┘
```

---

## 💰 成本分析

| 服務 | 免費額度 | 預計使用 | 成本 |
|------|----------|----------|------|
| Render Starter | - | 512MB RAM | $7/月 ✅ |
| Qdrant Cloud | 1GB + 10萬請求 | < 500MB + 5萬請求 | $0/月 ✅ |
| **總計** | | | **$7/月** |

---

## 📋 實施步驟

### Step 1: 註冊 Qdrant Cloud (1小時)
- [ ] 訪問 https://cloud.qdrant.io
- [ ] 創建免費集群
- [ ] 獲取 API Key

### Step 2: 安裝依賴 (30分鐘)
```bash
pip install qdrant-client sentence-transformers
```

### Step 3: 創建 QdrantTranslationMemory 類 (4小時)
```python
class QdrantTranslationMemory:
    def __init__(self, qdrant_url, api_key):
        self.client = QdrantClient(url=qdrant_url, api_key=api_key)
        self.embedder = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    
    def search(self, text, domain=None):
        # 1. 生成向量
        vector = self.embedder.encode(text)
        
        # 2. Qdrant 搜索
        results = self.client.search(
            collection_name=f"tm_{domain}",
            query_vector=vector,
            limit=3
        )
        
        return results
```

### Step 4: 集成到現有系統 (3小時)
- 修改 `enhanced_translation_service.py`
- 添加 Qdrant 作為第二級緩存

### Step 5: 測試與部署 (2小時)
- 本地測試
- 更新 Render 環境變量
- 部署驗證

---

## 🔧 代碼實現草稿

### qdrant_memory.py
```python
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
import os

class QdrantTranslationMemory:
    """Qdrant 向量搜索 - 方案E"""
    
    def __init__(self):
        self.url = os.getenv("QDRANT_URL")
        self.api_key = os.getenv("QDRANT_API_KEY")
        
        self.client = QdrantClient(url=self.url, api_key=self.api_key)
        self.embedder = SentenceTransformer(
            'paraphrase-multilingual-MiniLM-L12-v2',
            cache_folder='/tmp/models'  # Render 可寫目錄
        )
    
    def add(self, source, target, domain="general"):
        """添加翻譯對到 Qdrant"""
        vector = self.embedder.encode(source)
        
        self.client.upsert(
            collection_name=f"tm_{domain}",
            points=[{
                "id": hash(source),
                "vector": vector.tolist(),
                "payload": {
                    "source": source,
                    "target": target,
                    "domain": domain
                }
            }]
        )
    
    def search(self, query, domain="general", threshold=0.85):
        """向量相似性搜索"""
        vector = self.embedder.encode(query)
        
        results = self.client.search(
            collection_name=f"tm_{domain}",
            query_vector=vector.tolist(),
            limit=3,
            score_threshold=threshold
        )
        
        return [
            {
                "source": r.payload["source"],
                "target": r.payload["target"],
                "similarity": r.score
            }
            for r in results
        ]
```

### 集成到現有系統
```python
class EnhancedTranslationService:
    def __init__(self):
        # 方案A: SQLite 精確匹配
        self.sqlite_tm = TranslationMemory()
        
        # 方案E: Qdrant 模糊匹配 (可選)
        if os.getenv("QDRANT_URL"):
            from qdrant_memory import QdrantTranslationMemory
            self.qdrant_tm = QdrantTranslationMemory()
        else:
            self.qdrant_tm = None
    
    def search_tm(self, text, domain):
        """兩級搜索"""
        # 1. SQLite 精確匹配
        results = self.sqlite_tm.search(text, domain)
        if results:
            return results
        
        # 2. Qdrant 模糊匹配 (如果可用)
        if self.qdrant_tm:
            results = self.qdrant_tm.search(text, domain)
            if results:
                # 保存到 SQLite (加速下次查詢)
                for r in results:
                    if r["similarity"] >= 0.95:  # 高相似度才保存
                        self.sqlite_tm.add(text, r["target"], domain)
                return results
        
        return []
```

---

## 📊 性能預估

| 指標 | SQLite (方案A) | Qdrant (方案E) | 綜合 |
|------|----------------|----------------|------|
| 精確匹配速度 | < 5ms | - | < 5ms |
| 模糊匹配速度 | - | 50-100ms | 50-100ms |
| 命中率 | 40% | 70% | 75% |
| API 節省 | 40% | 70% | 75% |

---

## 🎯 階段目標

### 階段1: 方案A上線 (今天)
- ✅ SQLite 精確匹配
- ✅ 術語表管理
- ✅ 穩定部署

### 階段2: 方案E集成 (1-2週後)
- 📝 Qdrant Cloud 設置
- 📝 向量搜索實現
- 📝 性能優化

---

## 🔗 相關資源

- Qdrant Cloud: https://cloud.qdrant.io
- Qdrant Docs: https://qdrant.tech/documentation/
- sentence-transformers: https://www.sbert.net/

---

**方案E將在方案A穩定運行後開始實施。**
