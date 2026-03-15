# GeBuDiu WhatsApp 整合 - 快速開始指南

> **預計整合時間**: 15-20 分鐘

---

## 📋 已創建的文件

| 文件 | 大小 | 說明 |
|------|------|------|
| `whatsapp_module.py` | 29.9 KB | 核心 WhatsApp 服務模組 |
| `whatsapp_routes.py` | 18.6 KB | Flask Blueprint API 路由 |
| `whatsapp_ui.html` | 37.6 KB | 前端 UI 組件（可嵌入 index.html） |
| `WHATSAPP_INTEGRATION.md` | 20.6 KB | 完整整合文檔 |
| `app_enhanced_whatsapp_integration.py` | 11.1 KB | 整合示例代碼 |

---

## 🚀 三步整合

### 步驟 1: 複製文件

將以下文件複製到 `C:\Users\Owner\cloudflare\Docx\gebudiu-api\` 目錄：

```
whatsapp_module.py
whatsapp_routes.py
whatsapp_ui.html
```

### 步驟 2: 修改 app_enhanced.py

在 `app_enhanced.py` 中進行以下修改：

#### 2.1 添加導入（在文件頂部，現有導入之後）

```python
# WhatsApp 整合
try:
    from whatsapp_routes import init_whatsapp_routes, WHATSAPP_AVAILABLE
    WHATSAPP_ENABLED = True
except ImportError as e:
    WHATSAPP_ENABLED = False
    logging.warning(f"WhatsApp integration not available: {e}")
```

#### 2.2 註冊 Blueprint（在 `init_services()` 函數末尾）

```python
# 初始化 WhatsApp 整合
if WHATSAPP_ENABLED:
    try:
        init_whatsapp_routes(app)
        logger.info("✅ WhatsApp integration initialized")
        app.config['WHATSAPP_ENABLED'] = True
    except Exception as e:
        logger.error(f"Failed to initialize WhatsApp: {e}")
        app.config['WHATSAPP_ENABLED'] = False
```

#### 2.3 更新 health() 端點（添加 WhatsApp 狀態）

在 `health()` 函數的 `status["features"]` 中添加：

```python
status["features"] = {
    # ... 原有功能 ...
    "whatsapp_integration": app.config.get('WHATSAPP_ENABLED', False)
}
```

### 步驟 3: 配置環境變量

在 `.env` 文件或 Render 環境變量中添加：

```bash
# 開發測試用（不發送真實消息）
WHATSAPP_PROVIDER=mock

# 生產環境（需要 Cloudwapi API Key）
# WHATSAPP_PROVIDER=cloudwapi
# CLOUDWAPI_API_KEY=your_api_key_here
# CLOUDWAPI_SENDER=85262322466

# 數據庫路徑
WHATSAPP_DB_PATH=/data/whatsapp.db

# 前端 URL（用於分享消息中的鏈接）
FRONTEND_URL=https://your-domain.onrender.com

# 公司名稱（用於分享消息）
COMPANY_NAME=GeBuDiu 翻譯服務
```

---

## 🎨 前端整合（可選）

### 嵌入分享 UI

1. 將 `whatsapp_ui.html` 的內容複製到 `index.html` 的 `</body>` 標籤之前

2. 在翻譯完成後顯示分享按鈕：

```javascript
// 翻譯完成後調用
function onTranslationComplete(fileInfo) {
    // 顯示 WhatsApp 分享按鈕
    document.getElementById('whatsapp-share-btn').classList.remove('hidden');
    
    // 綁定點擊事件
    document.getElementById('whatsapp-share-btn').onclick = function() {
        showWhatsAppShare(fileInfo);
    };
}
```

3. 添加分享按鈕 HTML：

```html
<button id="whatsapp-share-btn" class="whatsapp-share-trigger hidden">
    📱 分享到 WhatsApp
</button>
```

---

## ✅ 驗證整合

### 1. 啟動服務

```bash
cd C:\Users\Owner\cloudflare\Docx\gebudiu-api
python app_enhanced.py
```

### 2. 檢查健康狀態

```bash
curl http://localhost:5000/health
```

預期響應：
```json
{
    "status": "ok",
    "features": {
        "whatsapp_integration": true
    },
    "whatsapp": {
        "enabled": true,
        "provider": "mock"
    }
}
```

### 3. 測試 WhatsApp API

```bash
# 發送驗證碼（Mock 模式會打印到日誌）
curl -X POST http://localhost:5000/whatsapp/verify \
  -H "Content-Type: application/json" \
  -d '{"phone": "+85291234567"}'

# 驗證碼（使用返回的驗證碼）
curl -X POST http://localhost:5000/whatsapp/verify/code \
  -H "Content-Type: application/json" \
  -d '{"phone": "+85291234567", "code": "123456"}'
```

---

## 📊 API 端點列表

| 端點 | 方法 | 描述 |
|------|------|------|
| `/whatsapp/health` | GET | 健康檢查 |
| `/whatsapp/verify` | POST | 發送驗證碼 |
| `/whatsapp/verify/code` | POST | 驗證驗證碼 |
| `/whatsapp/user/profile` | GET | 獲取用戶資料 |
| `/whatsapp/user/profile` | PUT | 更新用戶資料 |
| `/whatsapp/share` | POST | 分享文件 |
| `/whatsapp/share/history` | GET | 分享歷史 |
| `/whatsapp/contacts` | GET | 獲取客戶通訊錄 |
| `/whatsapp/contacts` | POST | 添加客戶 |
| `/whatsapp/stats` | GET | 統計信息 |

---

## 🔧 故障排查

### 問題: WhatsApp 模組未加載

**症狀**: `/health` 顯示 `whatsapp_integration: false`

**解決**: 
1. 確認 `whatsapp_module.py` 和 `whatsapp_routes.py` 在同一目錄
2. 檢查 Python 依賴：`pip install requests`
3. 查看日誌：`grep -i whatsapp translation_enhanced.log`

### 問題: 驗證碼發送失敗

**症狀**: 調用 `/whatsapp/verify` 返回 500 錯誤

**解決**:
1. Mock 模式下正常，會打印到日誌
2. Cloudwapi 模式需要有效的 `CLOUDWAPI_API_KEY`
3. 檢查手機號格式是否正確

### 問題: 數據庫權限錯誤

**症狀**: `unable to open database file`

**解決**:
```bash
# 確保 /data 目錄存在且有寫入權限
mkdir -p /data
chmod 755 /data

# 或在開發環境使用本地路徑
export WHATSAPP_DB_PATH=./whatsapp.db
```

---

## 📱 WhatsApp Business 提供商

### Mock 模式（開發測試）
- 消息不會真實發送
- 驗證碼可在日誌中查看
- 適合本地開發測試

### Cloudwapi（生產環境）
- 需要註冊 Cloudwapi 帳號
- 獲取 API Key
- 支持發送文本和媒體

### Meta WhatsApp Business API（未來）
- 已預留接口
- 需要 Meta Business 認證
- 最穩定的官方方案

---

## 🎯 功能特性

### ✅ 已完成
- [x] WhatsApp 驗證登入（驗證碼機制）
- [x] 國際手機號格式支持
- [x] 文件分享到 WhatsApp
- [x] 客戶通訊錄管理
- [x] 分享歷史記錄
- [x] Mock 模式測試
- [x] Cloudwapi 整合
- [x] 前端 UI 組件

### 🚧 可擴展
- [ ] Meta WhatsApp Business API
- [ ] 文件直接上傳（而非鏈接）
- [ ] 群發功能
- [ ] 消息模板管理
- [ ] 發送狀態回調

---

## 📞 支持

如有問題，請參考：
1. `WHATSAPP_INTEGRATION.md` - 完整文檔
2. `whatsapp_ui.html` 中的註釋
3. 查看應用日誌：`translation_enhanced.log`

---

**整合完成後，外貿用戶即可：**
1. 🔐 使用 WhatsApp 快速驗證身份
2. 📤 一鍵分享翻譯文件給客戶
3. 📇 管理客戶通訊錄
4. 📊 查看分享歷史記錄
