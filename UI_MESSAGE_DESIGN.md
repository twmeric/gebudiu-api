# GeBuDiu UI 文案設計 - 翻譯等待提示

> 設計目標：降低用戶焦慮，建立信任感，明確設定期望

---

## 🎯 核心訊息

**翻譯可能需要 5-8 分鐘，這是正常的。**

原因：
- AI 正在逐句理解文檔語境
- 保持專業術語一致性
- 保留原始格式和排版

---

## 💡 推薦文案（分級展示）

### 方案 A：溫暖專業型（推薦）

```
🌟 正在精心翻譯您的文檔

預計需要 5-8 分鐘
請勿關閉頁面

✓ 已分析文檔結構
✓ 正在翻譯第 3/12 頁  
✓ 保持專業術語一致性
[==========>        ] 35%

💡 小提示：首次翻譯會較慢，後續同類文檔將提速 40%
```

### 方案 B：簡潔進階型

```
🔄 智能翻譯進行中

文件較大，預計 5-8 分鐘完成
這比傳統翻譯快 3 倍，且格式保留更完整

進度: [████████░░░░░░░░░░] 42%
已翻譯: 1250 / 3000 字

請保持頁面開啟，完成後自動下載
```

### 方案 C：專業透明型

```
⚙️ AI 深度翻譯處理中

文檔字數: 3,250 字
預計時間: 5-8 分鐘

處理階段:
[✓] 結構分析 (12s)
[✓] 領域識別 - 法律文件 (3s)
[→] 智能翻譯 (進行中，3-6 分鐘)
[ ] 格式保留處理 (1-2 分鐘)
[ ] 質量檢查 (30s)

為確保質量，這比實時預覽稍慢，但遠勝於簡單翻譯
```

---

## 🎨 UI 設計建議

### 1. 進度條設計

```css
.progress-container {
  width: 100%;
  max-width: 400px;
  margin: 20px auto;
}

.progress-bar {
  height: 8px;
  background: linear-gradient(90deg, #6366f1 0%, #8b5cf6 100%);
  border-radius: 4px;
  transition: width 0.5s ease;
  position: relative;
  overflow: hidden;
}

/* 流光效果 */
.progress-bar::after {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255,255,255,0.4),
    transparent
  );
  animation: shimmer 2s infinite;
}

@keyframes shimmer {
  100% { left: 100%; }
}
```

### 2. 階段指示器

```html
<div class="stage-indicator">
  <div class="stage active">
    <span class="icon">📄</span>
    <span class="text">分析</span>
  </div>
  <div class="stage active">
    <span class="icon">🤖</span>
    <span class="text">翻譯</span>
  </div>
  <div class="stage">
    <span class="icon">✨</span>
    <span class="text">優化</span>
  </div>
  <div class="stage">
    <span class="icon">📥</span>
    <span class="text">下載</span>
  </div>
</div>
```

### 3. 取消按鈕（可選）

```
不想等了？ [取消翻譯]

注意：取消後已翻譯內容將丟失
```

---

## 📝 文案原則

### ✅ DO
- 給出具體時間範圍 (5-8 分鐘)
- 解釋為什麼需要時間（質量保證）
- 展示具體進度（字數/頁數）
- 提供「首次慢，後續快」的預期

### ❌ DON'T
- 不要只說「請稍候」
- 不要顯示「載入中...」這種模糊訊息
- 不要讓用戶覺得是系統卡住

---

## 🌐 多語言版本

### 英文版
```
🌟 Carefully Translating Your Document

Estimated: 5-8 minutes
Please keep this page open

✓ Analyzing document structure
✓ Translating page 3/12
✓ Ensuring terminology consistency
[==========>        ] 35%

💡 Tip: First translation takes longer.
Similar documents will be 40% faster next time.
```

---

## 🔧 實現代碼片段

```javascript
// 動態更新預計時間
function updateEstimatedTime(progress, totalWords) {
  const remainingProgress = 100 - progress;
  const estimatedSeconds = (remainingProgress / 100) * 480; // 8分鐘 = 480秒
  
  const minutes = Math.ceil(estimatedSeconds / 60);
  
  if (minutes > 1) {
    return `預計還需 ${minutes} 分鐘`;
  } else {
    return `即將完成...`;
  }
}

// 階段文字更新
const stages = [
  { progress: 0, text: "正在分析文檔結構..." },
  { progress: 15, text: "識別專業領域..." },
  { progress: 25, text: "正在智能翻譯..." },
  { progress: 70, text: "保留原始格式..." },
  { progress: 90, text: "進行質量檢查..." },
  { progress: 100, text: "準備下載..." }
];
```

---

## 📊 A/B 測試建議

建議測試哪種文案能減少中途取消率：

| 版本 | 重點 | 測試指標 |
|------|------|----------|
| A | 溫暖專業 | 取消率、完成率 |
| B | 數據透明 | 用戶信任度調查 |
| C | 對比優勢 | 與競品比較認知 |

---

**推薦使用：方案 A（溫暖專業型）**
- 適合 GBD 的品牌調性
- 平衡了專業性和友好度
- 明確設定了時間預期
