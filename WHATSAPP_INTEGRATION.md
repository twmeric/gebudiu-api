# GeBuDiu WhatsApp 整合文檔

> **版本**: v1.0  
> **更新日期**: 2026-03-15  
> **適用項目**: GeBuDiu (GBD) 翻譯服務

---

## 目錄

1. [架構概覽](#架構概覽)
2. [數據庫結構](#數據庫結構)
3. [API 文檔](#api-文檔)
4. [前端整合](#前端整合)
5. [環境配置](#環境配置)
6. [使用示例](#使用示例)
7. [故障排查](#故障排查)

---

## 架構概覽

### 系統架構圖

```
┌─────────────────────────────────────────────────────────────────┐
│                      GeBuDiu 翻譯服務                           │
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │   app_enhanced  │    │  whatsapp_module │    │ whatsapp_   │ │
│  │     .py         │───▶│      .py         │───▶│ routes.py   │ │
│  │                 │    │  (核心邏輯)       │    │ (API 路由)   │ │
│  └─────────────────┘    └─────────────────┘    └──────┬──────┘ │
│         │                                             │        │
│         │                                             ▼        │
│         │                                    ┌─────────────┐   │
│         │                                    │  WhatsApp   │   │
│         │                                    │  Provider   │   │
│         │                                    │ (Cloudwapi) │   │
│         │                                    └─────────────┘   │
│         │                                             │        │
│         ▼                                             ▼        │
│  ┌─────────────────┐                         ┌─────────────┐   │
│  │  SQLite (/data) │                         │   用戶手機   │   │
│  │                 │                         │  (WhatsApp) │   │
│  │ • whatsapp_users│                         └─────────────┘   │
│  │ • whatsapp_shares                                         │
│  │ • whatsapp_contacts                                       │
│  └─────────────────┘                                          │
└─────────────────────────────────────────────────────────────────┘
```

### 整合特點

| 特性 | 說明 |
|------|------|
| **模塊化設計** | 使用 Flask Blueprint，不影響現有路由 |
| **多提供商支持** | 支持 Cloudwapi、Meta API（預留）、Mock 模式 |
| **外貿友好** | 支持國際號碼格式、客戶通訊錄管理 |
| **安全可靠** | 驗證碼機制、一次性使用、過期自動失效 |

---

## 數據庫結構

### 數據庫位置

```
/data/whatsapp.db  (生產環境)
./whatsapp.db      (開發環境)
```

### 表結構

#### 1. whatsapp_users - 用戶表

```sql
CREATE TABLE whatsapp_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone TEXT UNIQUE NOT NULL,           -- 國際格式: +852XXXXXXXX
    name TEXT,                             -- 用戶名稱
    company TEXT,                          -- 公司名稱
    verified BOOLEAN DEFAULT 0,            -- 是否已驗證
    verification_code TEXT,                -- 當前驗證碼
    code_expires_at TIMESTAMP,             -- 驗證碼過期時間
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP
);
```

#### 2. whatsapp_shares - 分享記錄表

```sql
CREATE TABLE whatsapp_shares (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,              -- 關聯用戶 ID
    file_name TEXT NOT NULL,               -- 文件名
    file_type TEXT NOT NULL,               -- 文件類型: docx, xlsx
    file_size INTEGER NOT NULL,            -- 文件大小（字節）
    target_phone TEXT,                     -- 目標客戶手機號
    target_name TEXT,                      -- 目標客戶名稱
    share_type TEXT NOT NULL,              -- self, customer, link
    share_link TEXT,                       -- 分享鏈接
    message_sent BOOLEAN DEFAULT 0,        -- 消息是否成功發送
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES whatsapp_users(id)
);
```

#### 3. whatsapp_contacts - 客戶通訊錄表

```sql
CREATE TABLE whatsapp_contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,              -- 關聯用戶 ID
    name TEXT NOT NULL,                    -- 客戶名稱
    phone TEXT NOT NULL,                   -- 客戶手機號
    company TEXT,                          -- 客戶公司
    notes TEXT,                            -- 備註
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES whatsapp_users(id),
    UNIQUE(user_id, phone)                 -- 同一用戶不能重複添加
);
```

### 索引

```sql
CREATE INDEX idx_whatsapp_users_phone ON whatsapp_users(phone);
CREATE INDEX idx_whatsapp_shares_user ON whatsapp_shares(user_id);
CREATE INDEX idx_whatsapp_contacts_user ON whatsapp_contacts(user_id);
```

---

## API 文檔

### 基礎信息

- **Base URL**: `/whatsapp`
- **認證方式**: Header `X-User-Phone`
- **Content-Type**: `application/json`

### 端點列表

#### 1. 健康檢查

```http
GET /whatsapp/health
```

**Response:**
```json
{
    "status": "ok",
    "available": true,
    "provider": "cloudwapi",
    "stats": {
        "total_users": 10,
        "verified_users": 8
    }
}
```

---

#### 2. 發送驗證碼

```http
POST /whatsapp/verify
```

**Request Body:**
```json
{
    "phone": "+85291234567"
}
```

**Response:**
```json
{
    "success": true,
    "message": "驗證碼已發送到您的 WhatsApp",
    "phone": "+85291234567",
    "expires_in": 600
}
```

**支持的手機號格式:**
- `+85291234567` (國際格式 - 推薦)
- `85291234567` (無 + 號)
- `0085291234567` (00 前綴)
- `91234567` (香港本地格式，自動添加 +852)
- `13800138000` (中國大陸，自動添加 +86)

---

#### 3. 驗證驗證碼

```http
POST /whatsapp/verify/code
```

**Request Body:**
```json
{
    "phone": "+85291234567",
    "code": "123456"
}
```

**Response (成功):**
```json
{
    "success": true,
    "message": "驗證成功",
    "user": {
        "id": 1,
        "phone": "+85291234567",
        "name": null,
        "company": null,
        "verified": true
    }
}
```

**Response (失敗):**
```json
{
    "success": false,
    "error": "INVALID_CODE",
    "message": "驗證碼錯誤，請重新輸入"
}
```

**錯誤碼:**
- `MISSING_PHONE` - 缺少手機號
- `MISSING_CODE` - 缺少驗證碼
- `USER_NOT_FOUND` - 用戶不存在
- `CODE_EXPIRED` - 驗證碼已過期
- `INVALID_CODE` - 驗證碼錯誤

---

#### 4. 獲取用戶資料

```http
GET /whatsapp/user/profile
X-User-Phone: +85291234567
```

**Response:**
```json
{
    "success": true,
    "user": {
        "id": 1,
        "phone": "+85291234567",
        "name": "張三",
        "company": "ABC Trading Ltd",
        "verified": true,
        "created_at": "2026-03-15T10:00:00"
    }
}
```

---

#### 5. 更新用戶資料

```http
PUT /whatsapp/user/profile
X-User-Phone: +85291234567
Content-Type: application/json

{
    "name": "張三",
    "company": "ABC Trading Ltd"
}
```

---

#### 6. 分享文件

```http
POST /whatsapp/share
X-User-Phone: +85291234567
Content-Type: application/json

{
    "file_name": "Purchase_Contract_2026.docx",
    "file_type": "docx",
    "file_size": 25600,
    "share_type": "customer",
    "target_phone": "+8613800138000",
    "target_name": "李四",
    "share_link": "https://gebudiu.io/download/abc123"
}
```

**share_type 說明:**
- `self` - 發送給自己
- `customer` - 發送給指定客戶（需要 target_phone）
- `link` - 生成分享鏈接

**Response:**
```json
{
    "success": true,
    "message": "文件分享成功",
    "share_id": 1,
    "sent_to": "+8613800138000",
    "share_link": "https://gebudiu.io/download/abc123"
}
```

---

#### 7. 獲取分享歷史

```http
GET /whatsapp/share/history?limit=20&client_phone=+8613800138000
X-User-Phone: +85291234567
```

**Query Parameters:**
- `limit` - 返回數量限制（默認 50）
- `client_phone` - 篩選特定客戶的記錄（可選）

**Response:**
```json
{
    "success": true,
    "history": [
        {
            "id": 1,
            "file_name": "Purchase_Contract_2026.docx",
            "file_type": "docx",
            "file_size": 25600,
            "target_phone": "+8613800138000",
            "target_name": "李四",
            "share_type": "customer",
            "share_link": "https://gebudiu.io/download/abc123",
            "message_sent": true,
            "created_at": "2026-03-15T10:30:00"
        }
    ],
    "count": 1
}
```

---

#### 8. 獲取客戶通訊錄

```http
GET /whatsapp/contacts
X-User-Phone: +85291234567
```

**Response:**
```json
{
    "success": true,
    "contacts": [
        {
            "id": 1,
            "name": "李四",
            "phone": "+8613800138000",
            "company": "XYZ Import Co.",
            "notes": "重要客戶，偏好中文溝通",
            "created_at": "2026-03-10T09:00:00"
        },
        {
            "id": 2,
            "name": "John Smith",
            "phone": "+1234567890",
            "company": "ABC Trading",
            "notes": null,
            "created_at": "2026-03-12T14:30:00"
        }
    ],
    "count": 2
}
```

---

#### 9. 添加客戶

```http
POST /whatsapp/contacts
X-User-Phone: +85291234567
Content-Type: application/json

{
    "name": "王五",
    "phone": "+8613900139000",
    "company": "Global Export Ltd",
    "notes": "新客戶，首次合作"
}
```

---

#### 10. 獲取統計

```http
GET /whatsapp/stats
X-User-Phone: +85291234567
```

**Response:**
```json
{
    "success": true,
    "stats": {
        "provider": "cloudwapi",
        "total_users": 10,
        "verified_users": 8,
        "user_stats": {
            "total_shares": 15,
            "contacts": 5
        }
    }
}
```

---

## 前端整合

### 1. 在 app_enhanced.py 中註冊 Blueprint

```python
# 在文件頂部導入
from whatsapp_routes import init_whatsapp_routes, WHATSAPP_AVAILABLE

# 在 init_services() 函數中添加
if WHATSAPP_AVAILABLE:
    try:
        init_whatsapp_routes(app)
        logger.info("WhatsApp integration initialized")
    except Exception as e:
        logger.error(f"Failed to initialize WhatsApp: {e}")
```

### 2. 翻譯完成後的分享 UI

在翻譯完成頁面添加以下組件：

```html
<!-- WhatsApp 分享模態框 -->
<div id="whatsapp-share-modal" class="modal">
    <div class="modal-content">
        <h3>📱 分享到 WhatsApp</h3>
        
        <!-- 步驟 1: 驗證 -->
        <div id="verify-step" class="step">
            <p>請輸入您的 WhatsApp 手機號碼</p>
            <input type="tel" id="phone-input" placeholder="+852 9123 4567">
            <button onclick="sendVerificationCode()">發送驗證碼</button>
        </div>
        
        <!-- 步驟 2: 驗證碼 -->
        <div id="code-step" class="step hidden">
            <p>請輸入收到的 6 位驗證碼</p>
            <input type="text" id="code-input" maxlength="6" placeholder="123456">
            <button onclick="verifyCode()">驗證</button>
        </div>
        
        <!-- 步驟 3: 分享選項 -->
        <div id="share-step" class="step hidden">
            <p>選擇分享方式</p>
            <button onclick="shareToSelf()">📤 發送給自己</button>
            <button onclick="shareToCustomer()">👤 發送給客戶</button>
            <button onclick="generateLink()">🔗 生成分享鏈接</button>
        </div>
    </div>
</div>
```

### 3. JavaScript API 調用示例

```javascript
// 發送驗證碼
async function sendVerificationCode() {
    const phone = document.getElementById('phone-input').value;
    
    const response = await fetch('/whatsapp/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone })
    });
    
    const data = await response.json();
    if (data.success) {
        showStep('code-step');
        startCountdown(data.expires_in);
    } else {
        alert(data.message);
    }
}

// 驗證驗證碼
async function verifyCode() {
    const phone = document.getElementById('phone-input').value;
    const code = document.getElementById('code-input').value;
    
    const response = await fetch('/whatsapp/verify/code', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone, code })
    });
    
    const data = await response.json();
    if (data.success) {
        localStorage.setItem('whatsapp_phone', phone);
        showStep('share-step');
    } else {
        alert(data.message);
    }
}

// 分享文件
async function shareFile(shareType, targetPhone = null, targetName = null) {
    const phone = localStorage.getItem('whatsapp_phone');
    
    const fileInfo = {
        file_name: currentFile.name,
        file_type: currentFile.type,
        file_size: currentFile.size,
        share_type: shareType,
        target_phone: targetPhone,
        target_name: targetName,
        share_link: shareType === 'link' ? generatedLink : null
    };
    
    const response = await fetch('/whatsapp/share', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-User-Phone': phone
        },
        body: JSON.stringify(fileInfo)
    });
    
    const data = await response.json();
    if (data.success) {
        showNotification('分享成功！');
    } else {
        alert(data.message);
    }
}
```

---

## 環境配置

### 必需環境變量

```bash
# WhatsApp 提供商選擇: mock | cloudwapi | meta
WHATSAPP_PROVIDER=mock

# 數據庫路徑（可選，默認 /data/whatsapp.db）
WHATSAPP_DB_PATH=/data/whatsapp.db

# Cloudwapi 配置（使用 cloudwapi 時必需）
CLOUDWAPI_API_KEY=your_api_key_here
CLOUDWAPI_SENDER=85262322466

# Meta API 配置（預留，未來使用）
META_ACCESS_TOKEN=your_meta_token
META_PHONE_NUMBER_ID=your_phone_number_id

# 前端 URL（用於分享消息中的鏈接）
FRONTEND_URL=https://gebudiu.io

# 公司名稱（用於分享消息）
COMPANY_NAME=GeBuDiu 翻譯服務
```

### Render 部署配置

在 `render.yaml` 中添加：

```yaml
envVarGroups:
  - name: whatsapp-config
    envVars:
      - key: WHATSAPP_PROVIDER
        value: cloudwapi
      - key: WHATSAPP_DB_PATH
        value: /data/whatsapp.db
      - key: CLOUDWAPI_SENDER
        value: "85262322466"
      - key: FRONTEND_URL
        value: https://gebudiu.onrender.com
```

---

## 使用示例

### 完整流程示例

#### 1. 首次使用（驗證流程）

```bash
# 1. 發送驗證碼
curl -X POST https://api.gebudiu.io/whatsapp/verify \
  -H "Content-Type: application/json" \
  -d '{"phone": "+85291234567"}'

# 響應：驗證碼已發送到 WhatsApp

# 2. 驗證驗證碼
curl -X POST https://api.gebudiu.io/whatsapp/verify/code \
  -H "Content-Type: application/json" \
  -d '{"phone": "+85291234567", "code": "123456"}'

# 響應：驗證成功，返回用戶信息
```

#### 2. 分享翻譯文件給客戶

```bash
# 3. 先添加客戶到通訊錄（可選）
curl -X POST https://api.gebudiu.io/whatsapp/contacts \
  -H "Content-Type: application/json" \
  -H "X-User-Phone: +85291234567" \
  -d '{
    "name": "李四",
    "phone": "+8613800138000",
    "company": "XYZ Import Co.",
    "notes": "重要客戶"
  }'

# 4. 分享文件
curl -X POST https://api.gebudiu.io/whatsapp/share \
  -H "Content-Type: application/json" \
  -H "X-User-Phone: +85291234567" \
  -d '{
    "file_name": "Contract_2026_EN.docx",
    "file_type": "docx",
    "file_size": 25600,
    "share_type": "customer",
    "target_phone": "+8613800138000",
    "target_name": "李四",
    "share_link": "https://gebudiu.io/download/abc123"
  }'

# 客戶收到 WhatsApp 消息：
# "您好 李四，
#  
# 為您準備了翻譯文件：
# 文件名：Contract_2026_EN.docx
# 格式：DOCX
# 大小：25.0 KB
#  
# 下載鏈接：https://gebudiu.io/download/abc123
#  
# 由 GeBuDiu 翻譯服務提供專業翻譯"
```

#### 3. 查看分享歷史

```bash
# 查看所有分享記錄
curl https://api.gebudiu.io/whatsapp/share/history \
  -H "X-User-Phone: +85291234567"

# 查看發給特定客戶的記錄
curl "https://api.gebudiu.io/whatsapp/share/history?client_phone=+8613800138000" \
  -H "X-User-Phone: +85291234567"
```

---

## 故障排查

### 常見問題

#### 1. 驗證碼發送失敗

**現象**: 調用 `/whatsapp/verify` 返回錯誤

**可能原因**:
- 使用 Mock 模式（開發環境正常）
- Cloudwapi API Key 無效
- 手機號格式不正確

**解決方法**:
```bash
# 檢查配置
echo $WHATSAPP_PROVIDER
echo $CLOUDWAPI_API_KEY

# 檢查日誌
tail -f translation_enhanced.log | grep WhatsApp
```

#### 2. 驗證碼驗證失敗

**錯誤碼**: `CODE_EXPIRED`
- 驗證碼有效期為 10 分鐘，過期需要重新獲取

**錯誤碼**: `INVALID_CODE`
- 檢查輸入的驗證碼是否正確
- 注意區分 0 和 O，1 和 l

#### 3. 分享失敗

**錯誤碼**: `NOT_VERIFIED`
- 用戶未驗證，需要先完成驗證流程

**錯誤碼**: `MISSING_TARGET_PHONE`
- `share_type=customer` 時必須提供 `target_phone`

### 調試模式

設置環境變量啟用 Mock 模式進行測試：

```bash
export WHATSAPP_PROVIDER=mock
```

在 Mock 模式下，消息不會真正發送，但會記錄到日誌中。

### 日誌查看

```bash
# 查看 WhatsApp 相關日誌
grep -i whatsapp translation_enhanced.log

# 查看錯誤日誌
grep -i "whatsapp.*error" translation_enhanced.log
```

---

## 附錄

### 國際電話區碼參考

| 國家/地區 | 區碼 | 示例號碼 |
|-----------|------|----------|
| 中國大陸 | +86 | +8613800138000 |
| 香港 | +852 | +85291234567 |
| 澳門 | +853 | +85361234567 |
| 台灣 | +886 | +886912345678 |
| 美國 | +1 | +1234567890 |
| 英國 | +44 | +447123456789 |
| 新加坡 | +65 | +6581234567 |
| 馬來西亞 | +60 | +60123456789 |
| 日本 | +81 | +819012345678 |
| 韓國 | +82 | +821012345678 |

### 消息模板

系統使用以下消息模板：

**驗證碼消息**:
```
🌐 GeBuDiu 翻譯服務

您的驗證碼是：*123456*

此驗證碼 10 分鐘內有效。

如非本人操作，請忽略此消息。
```

**驗證成功消息**:
```
✅ 驗證成功！

歡迎使用 GeBuDiu 專業翻譯服務。

📄 您可以：
• 上傳 DOCX/XLSX 文件進行翻譯
• 翻譯完成後直接分享到 WhatsApp
• 管理客戶通訊錄

🌐 訪問：https://gebudiu.io
```

**文件分享消息**（給客戶）:
```
您好 李四，

為您準備了翻譯文件：

文件名：Contract_2026_EN.docx
格式：DOCX
大小：25.0 KB

📎 下載鏈接：https://gebudiu.io/download/abc123

🌐 由 GeBuDiu 翻譯服務提供專業翻譯
如有任何問題，請隨時聯繫。
```

---

*文檔版本: v1.0*  
*最後更新: 2026-03-15*
