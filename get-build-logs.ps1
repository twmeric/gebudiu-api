# Get build logs
$RENDER_API_KEY = "rnd_EbUsdRwqpF7XiAGhglOavLEbkgkG"
$BUILD_ID = "bld-d6rahtsr85hc73fmnm7g"

$headers = @{
    "Accept" = "application/json"
    "Authorization" = "Bearer $RENDER_API_KEY"
}

Write-Host "Fetching build details..." -ForegroundColor Cyan

try {
    $build = Invoke-RestMethod -Uri "https://api.render.com/v1/builds/$BUILD_ID" -Headers $headers
    Write-Host ($build | ConvertTo-Json -Depth 5) -ForegroundColor Green
} catch {
    Write-Host "Build endpoint failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`nTrying events for this build..." -ForegroundColor Yellow

try {
    $events = Invoke-RestMethod -Uri "https://api.render.com/v1/builds/$BUILD_ID/events" -Headers $headers
    Write-Host ($events | ConvertTo-Json -Depth 3) -ForegroundColor Green
} catch {
    Write-Host "Events endpoint failed: $($_.Exception.Message)" -ForegroundColor Red
}
