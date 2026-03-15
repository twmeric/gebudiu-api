# Qdrant Cloud 設置指南

> 方案E實施步驟

---

## 🎯 目標

在 Render 部署的應用中集成 Qdrant Cloud，提供向量模糊匹配功能。

---

## 📋 步驟 1: 註冊 Qdrant Cloud (5分鐘)

### 1.1 訪問 Qdrant Cloud
```
https://cloud.qdrant.io/
```

### 1.2 創建賬戶
- 可以使用 GitHub 或 Google 賬戶快速註冊
- 或使用郵箱註冊

### 1.3 創建免費集群
1. 點擊 "Create Cluster"
2. 選擇 "Free" 計劃
3. 選擇區域 (建議選擇離 Render 近的區域)
   - 推薦: `us-east` (如果 Render 在美國)
4. 等待集群創建 (約 2-3 分鐘)

---

## 📋 步驟 2: 獲取連接信息 (3分鐘)

### 2.1 獲取 URL
1. 進入集群詳情頁面
2. 複製 "Endpoint" URL
   ```
   https://xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx.us-east-0.aws.cloud.qdrant.io
   ```

### 2.2 創建 API Key
1. 點擊 "API Keys" 標籤
2. 點擊 "Create API Key"
3. 命名: `render-production`
4. 複製生成的 API Key
   ```
   xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

---

## 📋 步驟 3: 配置 Render 環境變量 (3分鐘)

### 3.1 訪問 Render Dashboard
```
https://dashboard.render.com/
```

### 3.2 找到 gebudiu-api 服務
1. 點擊 "gebudiu-api"
2. 進入 "Environment" 標籤

### 3.3 添加環境變量

| Key | Value |
|-----|-------|
| `QDRANT_URL` | `https://xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx.us-east-0.aws.cloud.qdrant.io` |
| `QDRANT_API_KEY` | `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |

### 3.4 保存並重新部署
- 點擊 "Save Changes"
- Render 會自動重新部署

---

## 📋 步驟 4: 初始化 Qdrant (2分鐘)

部署完成後，運行初始化腳本：

### 本地運行
```bash
export QDRANT_URL="https://xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx.us-east-0.aws.cloud.qdrant.io"
export QDRANT_API_KEY="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

python qdrant_setup.py setup
```

或

```bash
python qdrant_setup.py all
```

### 預期輸出
```
=== Step 1: Setup collections ===
Created collection: tm_general
Created collection: tm_electronics
Created collection: tm_medical
...
✅ Qdrant collections setup complete

=== Step 2: Migrate data ===
Found 150 entries in SQLite
Migrated 150/150 entries...
✅ Migration complete: 150 success, 0 failed

=== Step 3: Check status ===
✅ Qdrant connection successful
Collections:
   - tm_general: 50 points
   - tm_electronics: 40 points
   - tm_medical: 30 points
   ...
```

---

## ✅ 驗證

### API 測試
```bash
# 檢查健康狀態 (應該顯示 use_qdrant: true)
curl https://gebudiu-api.onrender.com/health

# 預期響應:
# {
#   "status": "ok",
#   "version": "3.2.0",
#   "enhanced_mode": true,
#   "use_qdrant": true,
#   ...
# }

# 檢查 Qdrant 統計
curl https://gebudiu-api.onrender.com/health
# 查看 qdrant_stats 字段
```

---

## 💰 成本說明

| 服務 | 免費額度 | 預計使用 | 成本 |
|------|----------|----------|------|
| Qdrant Cloud | 1GB + 10萬請求/月 | < 500MB + 5萬請求 | $0 |
| Render | 512MB RAM | 正常運行 | $7/月 |
| **總計** | | | **$7/月** |

---

## 🚨 常見問題

### 問題 1: "Qdrant not available"
**原因**: 環境變量未設置  
**解決**: 檢查 Render Dashboard 中的 `QDRANT_URL` 和 `QDRANT_API_KEY`

### 問題 2: 連接超時
**原因**: 網絡問題或 URL 錯誤  
**解決**: 
1. 確認 URL 格式正確
2. 檢查 API Key 是否有效
3. 嘗試重新生成 API Key

### 問題 3: 集合創建失敗
**原因**: 權限問題  
**解決**: 
1. 確認 API Key 有寫入權限
2. 在 Qdrant Dashboard 手動創建集合

---

## 🎯 完成標準

- [ ] Qdrant Cloud 賬戶創建
- [ ] 免費集群啟動
- [ ] URL 和 API Key 獲取
- [ ] Render 環境變量設置
- [ ] 初始化腳本運行成功
- [ ] API 測試通過

---

**預計總時間: 15-20 分鐘**
