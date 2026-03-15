# GeBuDiu API 用户指南

> 专业的 DOCX 文档翻译服务  
> 🌐 在线服务: https://gebudiu-api.onrender.com  
> 💡 核心理念: **越翻译，格式越精准**

---

## 📑 目录

1. [快速开始](#快速开始)
2. [API 端点说明](#api-端点说明)
3. [使用示例](#使用示例)
4. [功能介绍](#功能介绍)
   - [Translation Memory](#translation-memory)
   - [Domain Detection](#domain-detection)
   - [Terminology Management](#terminology-management)
   - [Format Self-Learning](#format-self-learning)
5. [错误处理](#错误处理)
6. [最佳实践](#最佳实践)

---

## 🚀 快速开始

### 1. 服务状态检查

```bash
curl https://gebudiu-api.onrender.com/health
```

**响应示例:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "api": "up",
    "tm": "up",
    "worker": "up"
  }
}
```

### 2. 简单文本翻译

```bash
curl -X POST https://gebudiu-api.onrender.com/api/v1/translate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, world!",
    "source_lang": "en",
    "target_lang": "zh"
  }'
```

**响应示例:**
```json
{
  "translation": "你好，世界！",
  "source_lang": "en",
  "target_lang": "zh",
  "source": "api",
  "confidence": 0.95,
  "processing_time": 0.823
}
```

### 3. DOCX 文档翻译

```bash
curl -X POST https://gebudiu-api.onrender.com/api/v1/translate/docx \
  -F "file=@document.docx" \
  -F "source_lang=en" \
  -F "target_lang=zh"
```

---

## 📡 API 端点说明

### 基础信息

| 属性 | 值 |
|------|-----|
| 基础 URL | `https://gebudiu-api.onrender.com` |
| 协议 | HTTPS |
| 数据格式 | JSON |
| 字符编码 | UTF-8 |
| 速率限制 | 100 请求/分钟 |

### 端点列表

```
┌──────────────────────────────────────────────────────────────┐
│                      API 端点总览                             │
├──────────┬─────────┬─────────────────────────────────────────┤
│ 方法     │ 路径    │ 说明                                    │
├──────────┼─────────┼─────────────────────────────────────────┤
│ GET      │ /       │ 服务信息                                │
│ GET      │ /health │ 健康检查                                │
│ POST     │ /api/v1/translate │ 文本翻译                      │
│ POST     │ /api/v1/translate/docx │ DOCX 文档翻译            │
│ POST     │ /api/v1/tm/search │ 搜索翻译记忆库               │
│ GET      │ /api/v1/tm/stats │ 翻译记忆库统计                │
│ POST     │ /api/v1/domain/detect │ 检测文档领域               │
│ GET      │ /api/v1/terminology │ 获取术语库                 │
│ POST     │ /api/v1/terminology │ 添加术语                   │
└──────────┴─────────┴─────────────────────────────────────────┘
```

### 详细说明

#### 1. 健康检查

```http
GET /health
```

**响应:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "api": "up",
    "tm": "up",
    "worker": "up"
  }
}
```

---

#### 2. 文本翻译

```http
POST /api/v1/translate
Content-Type: application/json
```

**请求参数:**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `text` | string | ✅ | 待翻译文本 |
| `source_lang` | string | 可选 | 源语言代码 (默认: auto) |
| `target_lang` | string | ✅ | 目标语言代码 |
| `use_tm` | boolean | 可选 | 使用翻译记忆库 (默认: true) |
| `async` | boolean | 可选 | 异步模式，长文本推荐 (默认: false) |

**语言代码:**

| 代码 | 语言 |
|------|------|
| `zh` | 中文 |
| `en` | 英文 |
| `ja` | 日文 |
| `ko` | 韩文 |
| `auto` | 自动检测 |

**请求示例:**
```json
{
  "text": "GeBuDiu API provides professional document translation services.",
  "source_lang": "en",
  "target_lang": "zh",
  "use_tm": true,
  "async": false
}
```

**响应示例:**
```json
{
  "translation": "GeBuDiu API 提供专业的文档翻译服务。",
  "source_lang": "en",
  "target_lang": "zh",
  "source": "api",
  "confidence": 0.96,
  "processing_time": 1.234
}
```

**TM 命中响应:**
```json
{
  "translation": "GeBuDiu API 提供专业的文档翻译服务。",
  "source_lang": "en",
  "target_lang": "zh",
  "source": "translation_memory",
  "confidence": 1.0,
  "processing_time": 0.023
}
```

**异步队列响应:**
```json
{
  "task_id": "abc123def456",
  "status": "queued",
  "message": "Translation queued for background processing"
}
```

---

#### 3. DOCX 文档翻译

```http
POST /api/v1/translate/docx
Content-Type: multipart/form-data
```

**请求参数:**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | file | ✅ | DOCX 文件 |
| `source_lang` | string | ✅ | 源语言代码 |
| `target_lang` | string | ✅ | 目标语言代码 |
| `preserve_format` | boolean | 可选 | 保留格式 (默认: true) |
| `domain` | string | 可选 | 指定领域 (自动检测覆盖) |

**响应示例:**
```json
{
  "download_url": "https://gebudiu-api.onrender.com/download/xyz789.docx",
  "expires_at": "2026-03-16T20:00:00Z",
  "pages": 5,
  "words": 1250,
  "estimated_time": 60
}
```

---

#### 4. 搜索翻译记忆库

```http
POST /api/v1/tm/search
Content-Type: application/json
```

**请求参数:**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `text` | string | ✅ | 搜索文本 |
| `source_lang` | string | ✅ | 源语言 |
| `target_lang` | string | ✅ | 目标语言 |

**响应示例:**
```json
{
  "query": "professional translation service",
  "matches": [
    {
      "source": "professional document translation services",
      "translation": "专业的文档翻译服务",
      "confidence": 0.92
    },
    {
      "source": "professional translation",
      "translation": "专业翻译",
      "confidence": 0.85
    }
  ]
}
```

---

#### 5. 翻译记忆库统计

```http
GET /api/v1/tm/stats
```

**响应示例:**
```json
{
  "total_entries": 15420,
  "language_pairs": [
    {"source_lang": "en", "target_lang": "zh", "count": 8750},
    {"source_lang": "zh", "target_lang": "en", "count": 6670}
  ],
  "faiss_index_size": 15420
}
```

---

#### 6. 领域检测

```http
POST /api/v1/domain/detect
Content-Type: application/json
```

**请求参数:**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `text` | string | ✅ | 待检测文本 |

**响应示例:**
```json
{
  "detected_domain": "legal",
  "confidence": 0.89,
  "candidates": [
    {"domain": "legal", "score": 0.89},
    {"domain": "financial", "score": 0.65},
    {"domain": "medical", "score": 0.23}
  ]
}
```

**支持领域:**

| 领域代码 | 中文名 | 适用场景 |
|----------|--------|----------|
| `general` | 通用 | 日常文档 |
| `legal` | 法律 | 合同、法规 |
| `medical` | 医学 | 病历、论文 |
| `financial` | 金融 | 财报、审计 |
| `technical` | 技术 | 手册、规范 |
| `marketing` | 营销 | 广告、宣传 |

---

#### 7. 术语库管理

**获取术语库:**
```http
GET /api/v1/terminology?domain=legal
```

**响应示例:**
```json
{
  "domain": "legal",
  "terms": [
    {"source": "contract", "target": "合同", "priority": "high"},
    {"source": "liability", "target": "责任", "priority": "high"},
    {"source": "jurisdiction", "target": "管辖权", "priority": "medium"}
  ]
}
```

**添加术语:**
```http
POST /api/v1/terminology
Content-Type: application/json
```

**请求示例:**
```json
{
  "domain": "technical",
  "source": "API",
  "target": "应用程序接口",
  "priority": "high"
}
```

---

## 💻 使用示例

### Python 示例

#### 文本翻译
```python
import requests

API_BASE = "https://gebudiu-api.onrender.com"

def translate_text(text, source_lang="en", target_lang="zh"):
    response = requests.post(
        f"{API_BASE}/api/v1/translate",
        json={
            "text": text,
            "source_lang": source_lang,
            "target_lang": target_lang
        }
    )
    return response.json()

# 使用示例
result = translate_text(
    "GeBuDiu API makes document translation easy.",
    source_lang="en",
    target_lang="zh"
)
print(result["translation"])
# 输出: GeBuDiu API 让文档翻译变得简单。
```

#### 批量翻译
```python
def batch_translate(texts, target_lang="zh"):
    results = []
    for text in texts:
        result = translate_text(text, target_lang=target_lang)
        results.append(result["translation"])
    return results

# 批量翻译
documents = [
    "Introduction",
    "Product Features",
    "User Guide",
    "Technical Specifications"
]
translations = batch_translate(documents, target_lang="zh")
```

#### DOCX 文档翻译
```python
def translate_docx(file_path, source_lang="en", target_lang="zh"):
    with open(file_path, 'rb') as f:
        files = {'file': f}
        data = {
            'source_lang': source_lang,
            'target_lang': target_lang
        }
        response = requests.post(
            f"{API_BASE}/api/v1/translate/docx",
            files=files,
            data=data
        )
    
    result = response.json()
    
    # 下载翻译后的文件
    if 'download_url' in result:
        download_response = requests.get(result['download_url'])
        with open('translated_document.docx', 'wb') as f:
            f.write(download_response.content)
    
    return result

# 使用示例
translate_docx('contract.docx', source_lang='en', target_lang='zh')
```

---

### JavaScript/Node.js 示例

#### 文本翻译
```javascript
const API_BASE = 'https://gebudiu-api.onrender.com';

async function translateText(text, sourceLang = 'en', targetLang = 'zh') {
  const response = await fetch(`${API_BASE}/api/v1/translate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      text,
      source_lang: sourceLang,
      target_lang: targetLang,
    }),
  });
  
  return response.json();
}

// 使用示例
translateText('Hello, world!', 'en', 'zh')
  .then(result => console.log(result.translation));
```

#### 领域检测
```javascript
async function detectDomain(text) {
  const response = await fetch(`${API_BASE}/api/v1/domain/detect`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ text }),
  });
  
  const result = await response.json();
  return result.detected_domain;
}

// 使用示例
detectDomain('This contract is governed by the laws of California.')
  .then(domain => console.log(domain));  // 输出: legal
```

---

### cURL 示例

```bash
#!/bin/bash

API_BASE="https://gebudiu-api.onrender.com"

# 1. 检查服务状态
echo "=== 检查服务状态 ==="
curl -s $API_BASE/health | jq .

# 2. 简单翻译
echo -e "\n=== 文本翻译 ==="
curl -s -X POST $API_BASE/api/v1/translate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Professional document translation service",
    "source_lang": "en",
    "target_lang": "zh"
  }' | jq .

# 3. 领域检测
echo -e "\n=== 领域检测 ==="
curl -s -X POST $API_BASE/api/v1/domain/detect \
  -H "Content-Type: application/json" \
  -d '{
    "text": "The patient was diagnosed with pneumonia."
  }' | jq .

# 4. TM 搜索
echo -e "\n=== 搜索翻译记忆库 ==="
curl -s -X POST $API_BASE/api/v1/tm/search \
  -H "Content-Type: application/json" \
  -d '{
    "text": "translation service",
    "source_lang": "en",
    "target_lang": "zh"
  }' | jq .

# 5. TM 统计
echo -e "\n=== 翻译记忆库统计 ==="
curl -s $API_BASE/api/v1/tm/stats | jq .
```

---

## 🎯 功能介绍

### Translation Memory (翻译记忆库)

**什么是翻译记忆库？**

翻译记忆库 (TM) 是一个存储源文本和译文对应关系的数据库。当您翻译过的内容再次出现，系统会自动提供之前的翻译，确保一致性和效率。

**工作原理:**

```
┌─────────────────────────────────────────────────────────────┐
│                    三级搜索策略                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1️⃣ 精确匹配 (Exact Match)                                  │
│     └── 文本完全一致，100% 置信度，即时返回                   │
│     └── 响应时间: <10ms                                      │
│                                                              │
│  2️⃣ 模糊匹配 (Fuzzy Match)                                  │
│     └── FTS5 全文搜索引擎，查找相似文本                       │
│     └── 置信度: 70-95%                                       │
│     └── 响应时间: <50ms                                      │
│                                                              │
│  3️⃣ 语义匹配 (Semantic Match)                               │
│     └── FAISS 向量相似度搜索，理解语义相似性                  │
│     └── 置信度: 70-90%                                       │
│     └── 响应时间: <100ms                                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**使用场景:**

| 场景 | 效果 |
|------|------|
| 合同翻译 | 法律术语保持一致 |
| 产品手册 | 技术术语统一 |
| 批量文档 | 重复内容自动匹配 |
| 更新版本 | 已有翻译自动复用 |

**API 控制:**
```json
{
  "text": "...",
  "use_tm": true,  // 启用翻译记忆库
  "target_lang": "zh"
}
```

---

### Domain Detection (领域检测)

**什么是领域检测？**

系统通过 AI 自动识别文档所属的专业领域（如法律、医学、金融等），并加载相应的术语库和翻译策略。

**检测领域:**

| 领域 | 典型内容 | 特殊处理 |
|------|----------|----------|
| `legal` | 合同、法规 | 严谨措辞，保留条款结构 |
| `medical` | 病历、论文 | 医学术语标准化 |
| `financial` | 财报、审计 | 数字格式，货币单位 |
| `technical` | 手册、规范 | 技术术语一致性 |
| `marketing` | 广告、宣传 | 本地化适应 |
| `general` | 日常文档 | 自然流畅表达 |

**使用方式:**

```python
# 方式1: 自动检测
translate_docx('contract.docx')  # 系统自动识别为 legal 领域

# 方式2: 手动指定
translate_docx('contract.docx', domain='legal')
```

**影响:**
- 加载领域特定术语库
- 调整翻译策略和风格
- 优化专业术语翻译

---

### Terminology Management (术语管理)

**什么是术语管理？**

确保专业术语在整篇文档中翻译一致。您可以自定义术语库，系统会优先使用您的定义。

**术语优先级:**

```
用户自定义术语 > 领域术语库 > 通用翻译
     (高)           (中)          (低)
```

**管理术语:**

```bash
# 添加术语
curl -X POST https://gebudiu-api.onrender.com/api/v1/terminology \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "technical",
    "source": "Machine Learning",
    "target": "机器学习",
    "priority": "high"
  }'

# 获取术语库
curl "https://gebudiu-api.onrender.com/api/v1/terminology?domain=legal"
```

**术语效果:**

| 原文 | 无术语管理 | 有术语管理 |
|------|------------|------------|
| API | 接口/应用程序接口/API | API (统一) |
| Contract | 合同/契约/协议 | 合同 (统一) |
| Pneumonia | 肺炎/肺部炎症 | 肺炎 (医学标准) |

---

### Format Self-Learning (格式自学习)

**什么是格式自学习？**

GeBuDiu API 的核心卖点。**"越翻译，格式越精准"**意味着系统会持续学习和改进格式保留能力。

**保留的格式元素:**

```
┌─────────────────────────────────────────────────────────────┐
│                    格式保留能力                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ✅ 段落样式                                                 │
│     ├── 对齐方式 (左/右/居中/两端)                          │
│     ├── 行距和段间距                                        │
│     └── 缩进设置                                            │
│                                                              │
│  ✅ 字符格式                                                 │
│     ├── 字体和字号                                          │
│     ├── 粗体 / 斜体 / 下划线                                │
│     ├── 字体颜色                                            │
│     └── 高亮/背景色                                         │
│                                                              │
│  ✅ 文档结构                                                 │
│     ├── 标题层级 (Heading 1-6)                              │
│     ├── 列表 (有序/无序)                                    │
│     └── 表格结构                                            │
│                                                              │
│  🔄 持续优化中                                               │
│     ├── 图片位置                                            │
│     ├── 页眉页脚                                            │
│     └── 复杂表格                                            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**自学习机制:**

```
用户上传文档
      ↓
系统分析原文格式特征
      ↓
翻译内容
      ↓
应用学习到的格式规则
      ↓
生成格式一致的译文
      ↓
记录格式映射关系 (用于下次优化)
```

---

## ⚠️ 错误处理

### 错误响应格式

```json
{
  "error": {
    "code": "INVALID_LANGUAGE",
    "message": "Unsupported target language: xx",
    "details": {
      "supported_languages": ["zh", "en", "ja", "ko"]
    }
  }
}
```

### 错误码列表

| HTTP 状态码 | 错误码 | 说明 | 解决方案 |
|-------------|--------|------|----------|
| 400 | `INVALID_REQUEST` | 请求格式错误 | 检查 JSON 格式 |
| 400 | `MISSING_FIELD` | 缺少必填字段 | 检查 `text` 和 `target_lang` |
| 400 | `INVALID_LANGUAGE` | 不支持的语言 | 使用支持的语言代码 |
| 400 | `FILE_TOO_LARGE` | 文件过大 | 文件大小限制 10MB |
| 400 | `INVALID_FILE_TYPE` | 不支持的文件类型 | 仅支持 DOCX 格式 |
| 429 | `RATE_LIMITED` | 请求过于频繁 | 降低请求频率 |
| 500 | `TRANSLATION_ERROR` | 翻译服务错误 | 稍后重试 |
| 503 | `SERVICE_UNAVAILABLE` | 服务暂时不可用 | 检查 /health 端点 |

### 常见错误处理示例

```python
import requests

API_BASE = "https://gebudiu-api.onrender.com"

def safe_translate(text, target_lang):
    try:
        response = requests.post(
            f"{API_BASE}/api/v1/translate",
            json={"text": text, "target_lang": target_lang},
            timeout=30
        )
        
        if response.status_code == 429:
            print("请求过于频繁，请稍后再试")
            return None
        elif response.status_code == 400:
            error = response.json()
            print(f"请求错误: {error['message']}")
            return None
        elif response.status_code != 200:
            print(f"服务器错误: {response.status_code}")
            return None
        
        return response.json()
        
    except requests.Timeout:
        print("请求超时，建议使用异步模式")
        return None
    except Exception as e:
        print(f"请求异常: {e}")
        return None
```

---

## 💡 最佳实践

### 1. 翻译优化建议

```
✅ 推荐做法:
   ├── 批量短文本优先使用同步模式
   ├── 长文档 (>5000 字) 使用异步模式
   ├── 重复内容多的文档开启 TM
   └── 专业文档指定 domain 参数

❌ 避免做法:
   ├── 单请求翻译过长文本 (>10000 字)
   ├── 频繁请求相同内容 (使用 TM)
   └── 忽略领域检测 (影响专业术语)
```

### 2. 性能优化

| 技巧 | 效果 |
|------|------|
| 启用 TM | 减少 40-60% API 调用 |
| 批量处理 | 减少网络开销 |
| 异步模式 | 避免超时，支持大文档 |
| 本地缓存 | 缓存 TM 结果 |

### 3. 质量保证

```python
# 1. 先检测领域
domain = detect_domain(text)

# 2. 检查术语库
terminology = get_terminology(domain)

# 3. 执行翻译
result = translate(
    text,
    domain=domain,
    use_tm=True
)

# 4. 质量检查（人工或自动）
if result['confidence'] < 0.8:
    flag_for_review()
```

### 4. 集成建议

**CMS/网站集成:**
```javascript
// 页面加载完成后异步预加载 TM
window.addEventListener('load', () => {
  fetch(`${API_BASE}/api/v1/tm/stats`)
    .then(r => r.json())
    .then(stats => console.log('TM ready:', stats));
});
```

**文档处理工作流:**
```python
# 批量处理文件夹
def process_folder(folder_path):
    for docx_file in Path(folder_path).glob('*.docx'):
        # 1. 检测领域
        domain = detect_domain(docx_file)
        
        # 2. 翻译文档
        result = translate_docx(docx_file, domain=domain)
        
        # 3. 记录统计
        log_translation(result)
```

---

## 📞 支持

如有问题或建议，请通过以下方式联系:

- 📧 邮箱: support@gebudiu.com
- 🐛 问题反馈: https://github.com/gebudiu/api/issues
- 📖 文档: https://gebudiu-api.onrender.com/docs

---

**文档版本**: v1.0  
**最后更新**: 2026-03-15  
**API 版本**: v1.0
