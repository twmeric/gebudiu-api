# Try different log endpoints
$RENDER_API_KEY = "rnd_EbUsdRwqpF7XiAGhglOavLEbkgkG"
$DEPLOY_ID = "dep-d6rahtsr85hc73fmnm70"
$SERVICE_ID = "srv-d6q9edv5r7bs738d05n0"

$headers = @{
    "Accept" = "application/json"
    "Authorization" = "Bearer $RENDER_API_KEY"
}

Write-Host "Trying different log endpoints..." -ForegroundColor Cyan

# Try deploy logs
Write-Host "`n1. Deploy logs endpoint:" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "https://api.render.com/v1/deploys/$DEPLOY_ID/logs" -Headers $headers
    Write-Host $response -ForegroundColor Green
} catch {
    Write-Host "Failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Try service logs
Write-Host "`n2. Service logs endpoint:" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "https://api.render.com/v1/services/$SERVICE_ID/logs" -Headers $headers
    Write-Host $response -ForegroundColor Green
} catch {
    Write-Host "Failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Try events
Write-Host "`n3. Events endpoint:" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "https://api.render.com/v1/services/$SERVICE_ID/events" -Headers $headers
    Write-Host ($response | ConvertTo-Json -Depth 3) -ForegroundColor Green
} catch {
    Write-Host "Failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Get deploy details
Write-Host "`n4. Deploy details:" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "https://api.render.com/v1/services/$SERVICE_ID/deploys" -Headers $headers
    Write-Host ($response | ConvertTo-Json -Depth 5) -ForegroundColor Green
} catch {
    Write-Host "Failed: $($_.Exception.Message)" -ForegroundColor Red
}
