# 格不丢 API 部署指南

## 部署到 Render (免费)

### 方法 1: 使用 Render Dashboard (推荐)

1. **Fork 或下载代码**
   ```bash
   # 确保以下文件在当前目录:
   # - app.py
   # - requirements.txt
   # - Procfile
   ```

2. **登录 Render**
   - 访问 https://dashboard.render.com
   - 用 GitHub 账号登录

3. **创建 Web Service**
   - 点击 "New" → "Web Service"
   - 选择你的 GitHub 仓库
   - 或使用 "Upload Code" 直接上传

4. **配置服务**
   ```
   Name: gebudiu-api
   Runtime: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120
   Plan: Free
   ```

5. **添加环境变量**
   - 在 "Environment" 标签页添加:
   ```
   DEEPSEEK_API_KEY=sk-37a56b14534e450fbe6068c95cff4044
   ```

6. **部署**
   - 点击 "Create Web Service"
   - 等待部署完成 (约 2-3 分钟)

### 方法 2: 使用 Render CLI

```bash
# 安装 Render CLI
curl -fsSL https://render.com/install.sh | bash

# 登录
render login

# 部署
render deploy
```

## 部署后配置

### 获取 API 地址
部署完成后，你会获得类似这样的地址:
```
https://gebudiu-api.onrender.com
```

### 更新前端 API URL
修改 `gebudiu-landing/index.html` 中的 API_URL:
```javascript
const API_URL = 'https://gebudiu-api.onrender.com/translate';
```

然后重新部署前端:
```bash
cd gebudiu-landing
npx wrangler pages deploy . --project-name=gebudiu
```

## 免费版限制

| 项目 | 限制 |
|------|------|
| 内存 | 512 MB |
| 请求超时 | 120 秒 |
| 每月请求时长 | 750 小时 |
| 文件大小 | 最大 16MB |

## API 端点

### 健康检查
```bash
GET https://gebudiu-api.onrender.com/health
```

### 获取领域列表
```bash
GET https://gebudiu-api.onrender.com/domains
```

### 翻译文件
```bash
POST https://gebudiu-api.onrender.com/translate
Content-Type: multipart/form-data

file: <文件>
domain: general (可选)
```

## 故障排除

### 部署失败
1. 检查 `requirements.txt` 是否包含所有依赖
2. 检查 `Procfile` 格式是否正确
3. 查看 Render Dashboard 的日志

### API 返回 504 超时
- 文件可能太大，尝试减小文件
- 或者增加 gunicorn 的 `--timeout` 参数

### 翻译质量不佳
- 确保选择了正确的专业领域
- 检查 DeepSeek API Key 是否有效
