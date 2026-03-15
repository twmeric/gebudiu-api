# GeBuDiu 域名遷移記錄

## 📋 遷移概覽

| 項目 | 舊域名 | 新域名 | 狀態 |
|------|--------|--------|------|
| **前端頁面** | `gebudiu.pages.dev` | `gbd.jkdcoding.com` | 🔄 待切換 |
| **API 服務** | `gebudiu-api.onrender.com` | - | ✅ 保持不變 |
| **文檔站點** | - | `docs.gbd.jkdcoding.com` (可選) | 📋 規劃中 |

---

## 🎯 遷移原因

1. **品牌統一性**：使用 jkdcoding.com 主域名，強化品牌認知
2. **用戶信任**：自定義域名比 pages.dev 更顯專業
3. **SEO 優化**：更易於搜索引擎收錄和記憶
4. **未來擴展**：便於後續添加更多子服務（如 docs.gbd.jkdcoding.com）

---

## 🔧 技術配置

### 1. Cloudflare Pages 配置

```yaml
# Cloudflare Pages 項目設置
項目名稱: gebudiu
當前域名: gebudiu.pages.dev
目標域名: gbd.jkdcoding.com

DNS 配置:
  類型: CNAME
  名稱: gbd
  目標: gebudiu.pages.dev
  代理狀態: 已代理 (橙色雲朵)
```

### 2. DNS 記錄（需要在 jkdcoding.com 域名管理中添加）

```
類型: CNAME
主機: gbd
指向: gebudiu.pages.dev
TTL: 自動
```

### 3. Cloudflare Pages 自定義域名設置

```
1. 登入 Cloudflare Dashboard
2. 進入 Pages 項目 → gebudiu
3. 點擊「自定義域」
4. 添加域: gbd.jkdcoding.com
5. 按照提示完成驗證
```

---

## 📝 需要更新的文件清單

### 前端項目（gebudiu.pages.dev）

```
□ index.html
  - API_BASE_URL: gebudiu-api.onrender.com (保持不變)
  - 頁面標題中的域名引用
  
□ README.md (如果有)
  - 更新訪問地址
  
□ package.json (如果有)
  - homepage 字段
```

### 後端 API 項目（gebudiu-api）

```
□ index.html (文檔頁面)
  - 第 830 行: 在線試用按鈕鏈接
  - 第 911-1377 行: 所有 API 示例中的 URL
  
□ README.md
  - 服務地址說明
  
□ render.yaml
  - 環境變量 (如需要)
```

### MotherBase 項目

```
□ 文檔索引
  - 更新 gebudiu 項目鏈接
```

---

## 🔄 遷移步驟

### Phase 1: 準備（已完成）
- [x] 記錄當前配置
- [x] 準備域名遷移文檔
- [x] 設計 UI 等待提示

### Phase 2: DNS 配置（待執行）
- [ ] 在 jkdcoding.com DNS 添加 CNAME 記錄
- [ ] 在 Cloudflare Pages 添加自定義域名
- [ ] 等待 SSL 證書自動頒發（通常 5-15 分鐘）

### Phase 3: 代碼更新（待執行）
- [ ] 更新前端項目中的所有域名引用
- [ ] 更新後端文檔頁面
- [ ] 更新 README 文件

### Phase 4: 驗證（待執行）
- [ ] 訪問 https://gbd.jkdcoding.com 確認正常
- [ ] 測試 API 調用
- [ ] 確認舊域名 302 重定向（可選）

### Phase 5: 清理（可選）
- [ ] 保留舊域名重定向 30 天
- [ ] 更新所有外部文檔鏈接

---

## ⚠️ 注意事項

### 1. 零停機時間
```
Cloudflare Pages 的域名遷移是無縫的：
- 新域名配置完成後，舊域名仍然可用
- 可以同時使用多個域名
- 不需要重新部署
```

### 2. API 地址不變
```
重要：API 端點保持不變
- 前端仍然調用 gebudiu-api.onrender.com
- 這是刻意設計的分離架構
- 未來 API 也可能遷移到 api.gbd.jkdcoding.com
```

### 3. SSL/HTTPS
```
Cloudflare 會自動為新域名頒發 SSL 證書
- 無需手動配置
- 自動續期
- 完全免費
```

---

## 🎨 新域名品牌設計

### Logo/圖標建議
```
gbd.jkdcoding.com
├── gbd: GeBuDiu 縮寫，品牌標識
├── jkdcoding: 公司/個人品牌
└── .com: 國際化
```

### 未來子域名規劃
```
gbd.jkdcoding.com          # 主站 - 翻譯服務
docs.gbd.jkdcoding.com     # 文檔中心
status.gbd.jkdcoding.com   # 服務狀態頁面
api.gbd.jkdcoding.com      # API 端點（未來遷移）
```

---

## 📞 聯繫與記錄

| 日期 | 事件 | 執行人 | 狀態 |
|------|------|--------|------|
| 2026-03-15 | 創建遷移文檔 | MotherBase | ✅ |
| - | DNS 配置 | - | 🔄 |
| - | 域名驗證 | - | 🔄 |
| - | 代碼更新 | - | 🔄 |
| - | 驗證測試 | - | 🔄 |

---

## 🔗 相關資源

- Cloudflare Pages 文檔: https://developers.cloudflare.com/pages/platform/custom-domains/
- 當前端點: https://gebudiu.pages.dev
- 目標端點: https://gbd.jkdcoding.com (待生效)
- API 服務: https://gebudiu-api.onrender.com
