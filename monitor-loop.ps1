# Auto-monitoring loop for Render deployment
$RENDER_API_KEY = "rnd_EbUsdRwqpF7XiAGhglOavLEbkgkG"
$SERVICE_NAME = "gebudiu-api"

$headers = @{
    "Accept" = "application/json"
    "Authorization" = "Bearer $RENDER_API_KEY"
}

Write-Host "=== Starting Render Deploy Monitor ===" -ForegroundColor Cyan
Write-Host "Monitoring service: $SERVICE_NAME" -ForegroundColor White
Write-Host ""

# Get service ID first
$services = Invoke-RestMethod -Uri "https://api.render.com/v1/services?limit=20" -Headers $headers
$service = $services | Where-Object { $_.service.name -eq $SERVICE_NAME }

if (-not $service) {
    Write-Host "Service not found!" -ForegroundColor Red
    exit 1
}

$serviceId = $service.service.id
Write-Host "Service ID: $serviceId" -ForegroundColor Green
Write-Host ""

# Monitor loop
$maxChecks = 30
$check = 0
$lastDeployId = $null

while ($check -lt $maxChecks) {
    $check++
    Write-Host "Check #$check / $maxChecks - $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Yellow
    
    # Get latest deploy
    $deploys = Invoke-RestMethod -Uri "https://api.render.com/v1/services/$serviceId/deploys?limit=1" -Headers $headers
    
    if ($deploys.Count -eq 0) {
        Write-Host "  No deploys yet, waiting..." -ForegroundColor Gray
        Start-Sleep 15
        continue
    }
    
    $deploy = $deploys[0].deploy
    $deployId = $deploy.id
    $status = $deploy.status
    $commitMsg = $deploy.commit.message
    
    if ($lastDeployId -ne $deployId) {
        Write-Host "  New deploy detected: $deployId" -ForegroundColor Cyan
        Write-Host "  Commit: $commitMsg" -ForegroundColor Gray
        $lastDeployId = $deployId
    }
    
    Write-Host "  Status: $status" -ForegroundColor $(switch($status) {
        "live" { "Green" }
        "build_failed" { "Red" }
        default { "White" }
    })
    
    switch ($status) {
        "live" {
            Write-Host "`n✅ DEPLOY SUCCESSFUL!" -ForegroundColor Green
            Write-Host "   URL: $($service.service.serviceDetails.url)" -ForegroundColor Green
            Write-Host "`nTesting health endpoint..." -ForegroundColor Yellow
            
            try {
                $health = Invoke-RestMethod -Uri "$($service.service.serviceDetails.url)/health" -TimeoutSec 10
                Write-Host "   Health check: $($health | ConvertTo-Json -Compress)" -ForegroundColor Green
            } catch {
                Write-Host "   Health check failed: $_" -ForegroundColor Red
            }
            
            exit 0
        }
        "build_failed" {
            Write-Host "`n❌ BUILD FAILED!" -ForegroundColor Red
            Write-Host "`nPossible fixes:" -ForegroundColor Yellow
            Write-Host "  1. Check if requirements.txt exists (should be renamed to requirements-local.txt)"
            Write-Host "  2. Check if render.yaml references correct requirements file"
            Write-Host "  3. Check if any Python file imports qdrant/sentence-transformers at module level"
            Write-Host "  4. Try clearing build cache in Render Dashboard"
            exit 1
        }
        "canceled" {
            Write-Host "`n⚠️ DEPLOY CANCELED" -ForegroundColor Yellow
            exit 1
        }
    }
    
    Write-Host "  Waiting 20 seconds..." -ForegroundColor Gray
    Start-Sleep 20
}

Write-Host "`n⚠️ TIMEOUT - Max checks reached" -ForegroundColor Yellow
