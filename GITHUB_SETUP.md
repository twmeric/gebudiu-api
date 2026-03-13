# GitHub + Render 部署指南

## 第一步：创建 GitHub 仓库

1. 访问 https://github.com/new
2. 仓库名称：`gebudiu-api`
3. 选择 Public 或 Private
4. **不要**勾选 "Initialize this repository with a README"
5. 点击 "Create repository"
6. 复制仓库地址（类似 `https://github.com/twmeric/gebudiu-api.git`）

## 第二步：推送代码到 GitHub

在当前目录打开终端/PowerShell，执行：

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/twmeric/gebudiu-api.git
git push -u origin main
```

## 第三步：在 Render 连接 GitHub

1. 回到 Render Dashboard (您现在所在的页面)
2. 选择 "Git Provider" (已选中)
3. 在下拉列表中找到并选择 `twmeric/gebudiu-api`
4. 点击 "Connect"

## 第四步：配置 Render

填写以下信息：

| 字段 | 值 |
|-----|-----|
| Name | gebudiu-api |
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120` |
| Plan | Free |

## 第五步：添加环境变量

点击 "Advanced" → "Environment Variables"，添加：

```
Key: DEEPSEEK_API_KEY
Value: sk-37a56b14534e450fbe6068c95cff4044
```

## 第六步：部署

点击 "Create Web Service"，等待 2-3 分钟部署完成。

部署成功后，您会得到类似 `https://gebudiu-api.onrender.com` 的地址。

把这个地址告诉我，我更新前端配置！
