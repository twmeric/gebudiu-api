# MotherBase AI Agent 守則

> 版本: 1.0
> 更新日期: 2026-03-16
> 適用範圍: 所有 MotherBase 協作項目

---

## 🎯 核心原則

### 1. 自動 DevOps 循環（強制）

**所有涉及部署、測試、修復的任務，必須遵循以下循環：**

```
┌─────────────────────────────────────────────────────────────┐
│                    自動 DevOps 循環                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. 監控 (Monitor)                                          │
│     └── 使用 CLI/API 獲取實時日誌                            │
│                                                              │
│  2. 分析 (Analyze)                                          │
│     └── AI 分析錯誤模式和根因                                │
│                                                              │
│  3. 設計 (Design)                                           │
│     └── 生成修復方案和代碼變更                               │
│                                                              │
│  4. 修復 (Fix)                                              │
│     └── 實施代碼修復                                         │
│                                                              │
│  5. 部署 (Deploy)                                           │
│     └── 自動部署並驗證                                       │
│                                                              │
│  6. 驗證 (Verify)                                           │
│     └── 確認問題解決，否則循環回到步驟 1                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**強制要求：**
- ✅ 任何部署後的錯誤必須自動捕獲
- ✅ 任何修復必須經過驗證才視為完成
- ✅ 保留完整的修復歷史記錄

---

## 🛠️ 平台特定指南

### Render 平台

**CLI 工具：**
```bash
# 監控部署
render deploys list --service srv-xxx
render logs --service srv-xxx --tail
```

**API 工具：**
```python
# 使用 Render REST API
GET https://api.render.com/v1/services/{service_id}/logs
GET https://api.render.com/v1/services/{service_id}/deploys
```

**標準流程：**
1. 每次推送後啟動 `monitor-loop.ps1`
2. 檢測到 `build_failed` 或 `update_failed` 自動觸發分析
3. 生成修復方案並實施
4. 重新部署並驗證

### Cloudflare Workers 平台

**CLI 工具：**
```bash
# 監控日誌
wrangler tail

# 部署
wrangler deploy
```

**標準流程：**
1. 使用 `wrangler tail` 捕獲實時日誌
2. 分析 Worker 異常和性能問題
3. 自動修復並重新部署

---

## 📋 錯誤處理優先級

| 級別 | 描述 | 響應時間 | 自動修復 |
|------|------|----------|----------|
| **P0** | 服務完全不可用 | 立即 | 是 |
| **P1** | 核心功能故障 | 30分鐘內 | 是 |
| **P2** | 非核心功能問題 | 2小時內 | 可選 |
| **P3** | 性能優化 | 24小時內 | 否 |

---

## 🔧 標準修復模式

### 模式 1：文件系統權限問題

**症狀：**
```
Permission denied: '/data'
No such file or directory: '/data/xxx'
```

**自動修復：**
```python
def _find_writable_path(self, preferred_path: str) -> str:
    """找到可寫入的路徑，按優先順序嘗試"""
    candidates = [
        preferred_path,                    # 首選
        "/tmp/" + basename,                 # 備選1
        os.path.expanduser("~/" + basename), # 備選2
        "./" + basename                     # 最終回退
    ]
    
    for path in candidates:
        if self._test_writable(path):
            return path
    
    return "./" + basename  # 最終回退
```

### 模式 2：依賴缺失

**症狀：**
```
ImportError: No module named 'xxx'
ModuleNotFoundError: No module named 'xxx'
```

**自動修復：**
```python
# 添加條件導入
try:
    from xxx import YYY
    XXX_AVAILABLE = True
except ImportError:
    XXX_AVAILABLE = False
    logger.warning("xxx not available, using fallback")
```

### 模式 3：超時問題

**症狀：**
```
WORKER TIMEOUT
Request timeout
```

**自動修復：**
- 增加 `GUNICORN_TIMEOUT` 環境變量
- 優化批處理大小
- 添加異步處理

---

## 📝 記錄要求

### 每次修復必須記錄：

1. **錯誤描述**
   - 錯誤類型
   - 影響範圍
   - 首次發生時間

2. **根因分析**
   - 技術原因
   - 環境因素
   - 觸發條件

3. **修復方案**
   - 代碼變更
   - 配置調整
   - 回退策略

4. **驗證結果**
   - 測試方法
   - 驗證通過標準
   - 監控指標

### 記錄格式：

```markdown
## 修復記錄 [YYYY-MM-DD HH:MM]

### 錯誤
- 類型: {error_type}
- 描述: {description}
- 來源: {service/platform}

### 分析
- 根因: {root_cause}
- 影響: {impact}

### 修復
- 文件: {file_changed}
- 變更: {code_change_summary}
- 提交: {commit_hash}

### 驗證
- 方法: {verification_method}
- 結果: {pass/fail}
- 狀態: {resolved/ongoing}
```

---

## 🤖 AI 代理行為準則

### DO（必須做）

✅ **主動監控**
- 每次部署後主動檢查日誌
- 設置合理的超時和重試機制
- 保持監控直到服務穩定

✅ **自動迭代**
- 第一次修復失敗，自動嘗試備選方案
- 記錄每次嘗試的結果
- 必要時請求人類介入

✅ **透明溝通**
- 明確說明當前步驟
- 預估完成時間
- 及時報告阻礙

### DON'T（禁止做）

❌ **盲目重試**
- 不分析原因就重複部署
- 忽視錯誤日誌中的警告
- 跳過驗證步驟

❌ **過度自信**
- 聲稱修復完成但未驗證
- 忽視環境差異（本地 vs 生產）
- 不考慮回退方案

❌ **知識丟失**
- 不修復文檔
- 不記錄修復過程
- 不更新守則

---

## 📚 參考資源

### 標準監控腳本

| 文件 | 用途 | 位置 |
|------|------|------|
| `monitor-loop.ps1` | 部署監控循環 | `gebudiu-api/` |
| `check-current.ps1` | 狀態檢查 | `gebudiu-api/` |
| `motherbase_auto_devops.py` | 完整 DevOps 自動化 | `gebudiu-api/` |
| `wrangler_auto_test.py` | Wrangler 測試 | `gebudiu-api/` |

### 平台文檔

- Render: https://render.com/docs
- Cloudflare Workers: https://developers.cloudflare.com/workers/
- Wrangler CLI: https://developers.cloudflare.com/workers/wrangler/

---

## 🔄 守則更新

**本守則應隨著實踐經驗不斷更新。**

每次重大修復後，應檢查是否需要：
- 添加新的錯誤模式
- 更新修復流程
- 完善驗證標準

---

**記住：自動 DevOps 循環不僅是工具，更是一種持續改進的文化。**

🚀 讓我們構建更健壯、更智能的系統！
