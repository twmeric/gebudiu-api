# Trigger deploy with cache clear
$RENDER_API_KEY = "rnd_EbUsdRwqpF7XiAGhglOavLEbkgkG"
$SERVICE_ID = "srv-d6q9edv5r7bs738d05n0"

$headers = @{
    "Accept" = "application/json"
    "Content-Type" = "application/json"
    "Authorization" = "Bearer $RENDER_API_KEY"
}

$body = @{
    clearCache = "clear"
} | ConvertTo-Json

Write-Host "Triggering deploy with cache clear..." -ForegroundColor Cyan

try {
    $response = Invoke-RestMethod -Uri "https://api.render.com/v1/services/$SERVICE_ID/deploys" -Method Post -Headers $headers -Body $body
    Write-Host "Deploy triggered successfully!" -ForegroundColor Green
    Write-Host ($response | ConvertTo-Json -Depth 3)
} catch {
    Write-Host "Failed: $_" -ForegroundColor Red
}
