# 格不丢翻譯 API - 增強版部署指南

## 🚀 新特性

### Translation Memory (TM)
- **FAISS + SQLite** 混合架構
- 向量相似性搜索
- 預期降低 API 成本 **50-70%**

### 智能領域檢測
- 自動識別文檔類型
- 優化翻譯質量
- 支持 7 大領域

### 翻譯質量評分
- 實時質量評估
- 提升用戶信任

---

## 📦 文件結構

```
gebudiu-api/
├── app_enhanced.py              # 增強版 Flask API
├── translation_memory.py        # TM 核心模塊
├── domain_detector.py           # 領域檢測器
├── enhanced_translation_service.py  # 增強翻譯服務
├── enhanced_docx_processor.py   # 增強 DOCX 處理器
├── requirements_enhanced.txt    # 依賴列表
├── render_enhanced.yaml         # Render 配置
├── wsgi_enhanced.py             # WSGI 入口
└── test_enhanced.py             # 測試腳本
```

---

## 🛠️ 本地測試

### 1. 安裝依賴

```bash
pip install -r requirements_enhanced.txt
```

### 2. 運行測試

```bash
python test_enhanced.py
```

### 3. 啟動服務

```bash
python app_enhanced.py
```

---

## 🌐 Render 部署

### 方法 1: 使用 Blueprint

1. 在 Render Dashboard 創建 Blueprint
2. 選擇 `render_enhanced.yaml`
3. 設置環境變量 `DEEPSEEK_API_KEY`

### 方法 2: 手動部署

1. 創建新的 Web Service
2. 選擇 Python 運行時
3. 配置:
   - Build Command: `pip install -r requirements_enhanced.txt`
   - Start Command: `gunicorn --bind 0.0.0.0:$PORT --timeout 600 wsgi_enhanced:app`
4. 添加 Disk (1GB) 用於 TM 存儲

---

## 📊 API 端點

### 健康檢查
```bash
GET /health
```

返回 TM 統計和系統狀態

### 翻譯文件
```bash
POST /translate
Content-Type: multipart/form-data

file: <docx/xlsx file>
domain: general (可選)
```

### TM 統計
```bash
GET /tm/stats
```

### 搜索 TM
```bash
POST /tm/search
Content-Type: application/json

{
  "query": "藍牙耳機",
  "domain": "electronics"
}
```

### 檢測領域
```bash
POST /detect-domain
Content-Type: application/json

{
  "filename": "product_spec.docx",
  "samples": ["藍牙", "規格"]
}
```

---

## 💰 成本優化預期

| 指標 | 當前 | 預期 | 節省 |
|------|------|------|------|
| API調用 | 100% | 30-50% | 50-70% |
| 翻譯速度 | 100% | 200% | 2x |
| 內存使用 | 100% | 85% | 15% |

---

## 🔧 配置選項

### 環境變量

| 變量 | 說明 | 默認值 |
|------|------|--------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密鑰 | 必需 |
| `TM_SIMILARITY_THRESHOLD` | TM 匹配閾值 | 0.85 |
| `TM_MAX_RESULTS` | 最大返回結果數 | 3 |
| `AUTO_DETECT_DOMAIN` | 自動檢測領域 | true |

---

## 📈 監控指標

響應頭包含以下指標:
- `X-Processing-Time`: 處理時間
- `X-API-Calls`: API 調用次數
- `X-TM-Hits`: TM 命中次數
- `X-Cache-Hits`: 緩存命中次數
- `X-Domain`: 檢測到的領域

---

## 🚨 注意事項

1. **首次啟動**: 會下載 118MB 的嵌入模型
2. **內存使用**: 總計約 420MB (在 Render 512MB 範圍內)
3. **磁盤使用**: TM 數據庫會持續增長，建議定期清理

---

## 🔮 未來擴展

- [ ] 術語表管理 UI
- [ ] TM 導入/導出
- [ ] 多語言支持
- [ ] 翻譯記憶共享

---

**部署時間**: 2026-03-15  
**版本**: v3.0.0 Enhanced
