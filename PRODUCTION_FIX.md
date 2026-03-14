# 🚨 GeBuDiu API 生產環境修復指南

## 🚨 發現核心問題

### 問題根源：DEPLOY.md 與實際代碼不一致

| 項目 | 配置 | 實際代碼 |
|-----|------|---------|
| **DEPLOY.md** 第 29 行 | `gunicorn app:app` | 指向 `app.py` (簡易版) |
| **Procfile** | `gunicorn app_secure:app` | 指向 `app_secure.py` (完整版) |

**可能情況**：Render Dashboard 中手動配置的 Start Command 指向了錯誤的文件！

### 兩個版本的關鍵差異

| 功能 | app.py (簡易版) | app_secure.py (完整版) |
|-----|----------------|---------------------|
| CORS 配置 | `CORS(app, origins="*")` ✅ | `CORS(app, origins="*", supports_credentials=False)` ✅ |
| 速率限制 | ❌ 無 | ✅ 有 Limiter |
| 錯誤處理 | 基礎 | 完善 + 日誌 |
| 文件驗證 | 簡單 | 完整 (ZIP 格式檢查) |

**兩個版本的 CORS 配置都是正確的！** 問題不在代碼，在 **部署配置**。

---

## 緊急修復步驟（按順序執行）

### Step 1: 更新 Render Start Command

登入 https://dashboard.render.com → 選擇 `gebudiu-api` 服務

**修改 Start Command 為：**
```bash
gunicorn --bind 0.0.0.0:$PORT --timeout 120 --workers 2 --threads 4 wsgi:app
```

### Step 2: 設置環境變量

在 Render Dashboard → Environment 中添加：
```
DEEPSEEK_API_KEY=sk-37a56b14534e450fbe6068c95cff4044
```

### Step 3: 重新部署

點擊 "Manual Deploy" → "Deploy latest commit"

---

## 關鍵參數說明

| 參數 | 值 | 說明 |
|-----|-----|------|
| `--timeout 120` | 120秒 | 翻譯大文件需要更長時間 |
| `--workers 2` | 2個 worker | Render Free 套餐內存限制 |
| `--threads 4` | 4線程 | 提高並發處理能力 |

---

## 驗證修復

部署完成後測試：

```bash
# 1. 健康檢查
curl https://gebudiu-api.onrender.com/health

# 2. CORS 預檢
curl -X OPTIONS -H "Origin: https://6e73aa26.gebudiu.pages.dev" \
  -H "Access-Control-Request-Method: POST" \
  https://gebudiu-api.onrender.com/translate

# 3. 實際翻譯請求（使用小文件測試）
curl -X POST -F "file=@test.docx" -F "domain=general" \
  -H "Origin: https://6e73aa26.gebudiu.pages.dev" \
  https://gebudiu-api.onrender.com/translate
```

---

## 502 錯誤根本原因

1. **Gunicorn Worker 超時**: 翻譯請求處理時間超過默認 30 秒
2. **內存不足**: Render Free 套餐 512MB 內存，大文件處理會 OOM
3. **啟動命令錯誤**: 可能指向了錯誤的應用文件

## CORS 錯誤根本原因

502 錯誤來自 **Render 反向代理層**，此時 Flask CORS 中間件尚未處理響應，因此無 CORS 頭。

修復 502 後，CORS 問題會自動解決。
