# 🔧 Python 3.14 構建問題修復記錄

## 問題位置
- **文件**: `C:\Users\Owner\cloudflare\Docx\gebudiu-api\render.yaml`
- **文件**: `C:\Users\Owner\cloudflare\Docx\gebudiu-api\requirements.txt`

## 問題描述
Render 使用 Python 3.14，構建 `sentence-transformers` 和 `qdrant-client` 時出現:
```
BackendUnavailable: Cannot import 'setuptools.build_meta'
```

## 修復方案

### 1. render.yaml 修改
```yaml
buildCommand: |
  pip install --upgrade pip setuptools wheel
  pip install qdrant-client==1.13.3 --no-build-isolation
  pip install sentence-transformers==2.3.1 --no-build-isolation
  pip install -r requirements.txt
```

**關鍵點**:
- 先安裝 `setuptools wheel`
- 使用 `--no-build-isolation` 禁用構建隔離
- 單獨安裝問題包

### 2. requirements.txt 修改
移除了 `qdrant-client` 和 `sentence-transformers`（已在 render.yaml 中安裝）

## 提交記錄
- **Commit**: e310d3d
- **時間**: 2026-03-15 14:55

## 驗證
部署完成後測試:
```bash
curl https://gebudiu-api.onrender.com/health
```
