# Render 部署監控與自動修復腳本
param(
    [string]$RenderApiKey = $env:RENDER_API_KEY,
    [string]$ServiceName = "gebudiu-api",
    [int]$MaxRetries = 5,
    [int]$CheckInterval = 30
)

$ErrorActionPreference = "Stop"

function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) { Write-Output $args }
    $host.UI.RawUI.ForegroundColor = $fc
}

function Get-RenderService {
    param($ApiKey, $ServiceName)
    
    try {
        $headers = @{
            "Accept" = "application/json"
            "Authorization" = "Bearer $ApiKey"
        }
        
        $services = Invoke-RestMethod -Uri "https://api.render.com/v1/services?limit=20" -Headers $headers
        
        foreach ($service in $services) {
            if ($service.service.name -eq $ServiceName) {
                return $service.service
            }
        }
        return $null
    }
    catch {
        Write-ColorOutput Red "❌ API 調用失敗: $_"
        return $null
    }
}

function Get-DeployStatus {
    param($ApiKey, $ServiceId)
    
    try {
        $headers = @{
            "Accept" = "application/json"
            "Authorization" = "Bearer $ApiKey"
        }
        
        $deploys = Invoke-RestMethod -Uri "https://api.render.com/v1/services/$ServiceId/deploys?limit=1" -Headers $headers
        
        if ($deploys -and $deploys.Count -gt 0) {
            return $deploys[0].deploy
        }
        return $null
    }
    catch {
        Write-ColorOutput Red "❌ 獲取部署狀態失敗: $_"
        return $null
    }
}

function Get-DeployLogs {
    param($ApiKey, $DeployId)
    
    try {
        $headers = @{
            "Accept" = "application/json"
            "Authorization" = "Bearer $ApiKey"
        }
        
        $logs = Invoke-RestMethod -Uri "https://api.render.com/v1/deploys/$DeployId/logs" -Headers $headers
        return $logs
    }
    catch {
        return $null
    }
}

function Test-BuildError {
    param($Logs)
    
    $errorPatterns = @(
        "Cannot import 'setuptools.build_meta'",
        "No module named 'setuptools'",
        "Failed to build",
        "ERROR: Could not build wheels",
        "Preparing metadata.*error",
        "Getting requirements.*error",
        "Building wheel.*error"
    )
    
    foreach ($pattern in $errorPatterns) {
        if ($Logs -match $pattern) {
            return $pattern
        }
    }
    return $null
}

function Fix-BuildError {
    Write-ColorOutput Yellow "🔧 自動修復: 檢測到 setuptools 構建錯誤"
    
    # 檢查 requirements-render.txt
    $reqFile = "requirements-render.txt"
    if (Test-Path $reqFile) {
        $content = Get-Content $reqFile -Raw
        
        # 如果還有問題包，徹底移除
        $problematic = @("sentence-transformers", "qdrant-client", "torch", "transformers")
        $fixed = $false
        
        foreach ($pkg in $problematic) {
            if ($content -match $pkg) {
                Write-ColorOutput Yellow "   移除問題包: $pkg"
                $content = $content -replace ".*$pkg.*", ""
                $fixed = $true
            }
        }
        
        if ($fixed) {
            # 清理空行並保存
            $content = ($content -split "`n" | Where-Object { $_.Trim() -ne "" }) -join "`n"
            Set-Content $reqFile $content -NoNewline
            
            # 同時更新 render.yaml 添加更多構建參數
            $yamlContent = @'
# Render 部署配置
services:
  - type: web
    name: gebudiu-api
    runtime: python
    plan: starter
    
    buildCommand: |
      pip install --upgrade pip==23.3.2 setuptools==69.0.3 wheel==0.42.0 --no-cache-dir --disable-pip-version-check
      pip install -r requirements-render.txt --no-cache-dir --disable-pip-version-check
    
    startCommand: gunicorn --bind 0.0.0.0:$PORT --timeout 600 --graceful-timeout 600 --keep-alive 60 --workers 1 --threads 1 --max-requests 100 wsgi:app
    
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
      - key: DEEPSEEK_API_KEY
        sync: false
      - key: PYTHONUNBUFFERED
        value: "1"
      - key: MALLOC_ARENA_MAX
        value: "2"
      - key: GUNICORN_TIMEOUT
        value: "600"
      - key: TM_DB_PATH
        value: /data/translation_memory.db
      - key: TERMINOLOGY_DB_PATH
        value: /data/terminology.db
      - key: ENHANCED_MODE
        value: "true"
    
    disk:
      name: data-disk
      mountPath: /data
      sizeGB: 1
    
    healthCheckPath: /health
    autoDeploy: true
'@
            Set-Content "render.yaml" $yamlContent
            
            # 提交更改
            git add -A
            git commit -m "Auto-fix: Remove problematic packages causing setuptools error"
            git push origin main
            
            Write-ColorOutput Green "✅ 自動修復完成，已推送新提交"
            return $true
        }
    }
    return $false
}

# ===== 主程序 =====

Write-ColorOutput Cyan "🚀 Render 部署監控與自動修復"
Write-Output ""

if (-not $RenderApiKey) {
    Write-ColorOutput Red "❌ 錯誤: 請設置 RENDER_API_KEY 環境變量"
    exit 1
}

# 獲取服務
$service = Get-RenderService -ApiKey $RenderApiKey -ServiceName $ServiceName

if (-not $service) {
    Write-ColorOutput Red "❌ 找不到服務: $ServiceName"
    exit 1
}

Write-ColorOutput Green "✅ 找到服務: $($service.name) (ID: $($service.id))"
Write-Output "   狀態: $($service.serviceDetails.state)"
Write-Output ""

# 監控部署
$retryCount = 0
$lastDeployId = $null

while ($retryCount -lt $MaxRetries) {
    $retryCount++
    
    Write-ColorOutput Cyan "⏳ 檢查 #$retryCount / $MaxRetries..."
    
    $deploy = Get-DeployStatus -ApiKey $RenderApiKey -ServiceId $service.id
    
    if (-not $deploy) {
        Write-ColorOutput Yellow "   無部署記錄，等待..."
        Start-Sleep $CheckInterval
        continue
    }
    
    $deployId = $deploy.id
    $status = $deploy.status
    
    if ($lastDeployId -ne $deployId) {
        Write-ColorOutput Green "   新部署: $deployId"
        $lastDeployId = $deployId
    }
    
    Write-Output "   狀態: $status"
    
    switch ($status) {
        "live" {
            Write-ColorOutput Green "`n✅ 部署成功!"
            Write-Output "   URL: $($service.serviceDetails.url)"
            exit 0
        }
        "build_failed" {
            Write-ColorOutput Red "`n❌ 構建失敗!"
            
            # 獲取日誌分析錯誤
            $logs = Get-DeployLogs -ApiKey $RenderApiKey -DeployId $deployId
            $errorPattern = Test-BuildError -Logs $logs
            
            if ($errorPattern) {
                Write-ColorOutput Yellow "   檢測到錯誤: $errorPattern"
                
                if (Fix-BuildError) {
                    Write-ColorOutput Cyan "`n🔄 等待新部署..."
                    $retryCount = 0
                    Start-Sleep ($CheckInterval * 2)
                    continue
                }
            }
            
            exit 1
        }
        "canceled" {
            Write-ColorOutput Yellow "`n⚠️ 部署被取消"
            exit 1
        }
        default {
            # 進行中狀態: created, build_in_progress, update_in_progress, etc.
            Write-Output "   進行中..."
        }
    }
    
    Start-Sleep $CheckInterval
}

Write-ColorOutput Yellow "`n⚠️ 達到最大重試次數，請手動檢查 Dashboard"
