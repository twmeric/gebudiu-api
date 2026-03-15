$RENDER_API_KEY = "rnd_EbUsdRwqpF7XiAGhglOavLEbkgkG"
$SERVICE_ID = "srv-d6q9edv5r7bs738d05n0"

$headers = @{
    "Accept" = "application/json"
    "Authorization" = "Bearer $RENDER_API_KEY"
}

Write-Host "Checking current deploy status..." -ForegroundColor Cyan

try {
    $deploys = Invoke-RestMethod -Uri "https://api.render.com/v1/services/$SERVICE_ID/deploys?limit=1" -Headers $headers
    $deploy = $deploys[0].deploy
    
    Write-Host "Deploy ID: $($deploy.id)" -ForegroundColor White
    Write-Host "Status: $($deploy.status)" -ForegroundColor $(switch($deploy.status) {
        "live" { "Green" }
        "build_failed" { "Red" }
        "update_failed" { "Red" }
        default { "Yellow" }
    })
    Write-Host "Commit: $($deploy.commit.message)" -ForegroundColor Gray
    Write-Host "Created: $($deploy.createdAt)" -ForegroundColor Gray
    
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
}
