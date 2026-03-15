# Render Deploy Monitor - Simple Version
$ErrorActionPreference = "Stop"

$RENDER_API_KEY = "rnd_EbUsdRwqpF7XiAGhglOavLEbkgkG"
$SERVICE_NAME = "gebudiu-api"

function Write-Status($msg, $color = "White") {
    Write-Host $msg -ForegroundColor $color
}

Write-Status "=== Render Deploy Monitor ===" "Cyan"
Write-Status ""

# Get service list
Write-Status "Fetching services..." "Yellow"

$headers = @{
    "Accept" = "application/json"
    "Authorization" = "Bearer $RENDER_API_KEY"
}

try {
    $services = Invoke-RestMethod -Uri "https://api.render.com/v1/services?limit=20" -Headers $headers
    
    $service = $services | Where-Object { $_.service.name -eq $SERVICE_NAME }
    
    if (-not $service) {
        Write-Status "Service '$SERVICE_NAME' not found!" "Red"
        Write-Status "Available services:" "Yellow"
        $services | ForEach-Object { Write-Status "  - $($_.service.name)" }
        exit 1
    }
    
    $serviceId = $service.service.id
    Write-Status "Found service: $($service.service.name) (ID: $serviceId)" "Green"
    Write-Status "Service state: $($service.service.serviceDetails.state)" "White"
    Write-Status "URL: $($service.service.serviceDetails.url)" "White"
    Write-Status ""
    
    # Get latest deploy
    Write-Status "Checking latest deploy..." "Yellow"
    
    $deploys = Invoke-RestMethod -Uri "https://api.render.com/v1/services/$serviceId/deploys?limit=1" -Headers $headers
    
    if ($deploys.Count -eq 0) {
        Write-Status "No deploys found!" "Red"
        exit 1
    }
    
    $deploy = $deploys[0].deploy
    $deployId = $deploy.id
    $status = $deploy.status
    $commit = $deploy.commit.message
    $createdAt = $deploy.createdAt
    
    Write-Status "Deploy ID: $deployId" "White"
    Write-Status "Status: $status" $(switch($status) { "live" { "Green" } "build_failed" { "Red" } default { "Yellow" }})
    Write-Status "Commit: $commit" "Gray"
    Write-Status "Created: $createdAt" "Gray"
    Write-Status ""
    
    # Get logs if build failed
    if ($status -eq "build_failed") {
        Write-Status "=== Fetching Build Logs ===" "Red"
        
        $logs = Invoke-RestMethod -Uri "https://api.render.com/v1/deploys/$deployId/logs" -Headers $headers
        
        # Look for specific errors
        $errorPatterns = @(
            "Cannot import 'setuptools.build_meta'",
            "Failed to build",
            "ERROR:.*error",
            "No module named"
        )
        
        $foundError = $false
        foreach ($pattern in $errorPatterns) {
            if ($logs -match $pattern) {
                Write-Status "Found error pattern: $pattern" "Red"
                $foundError = $true
                
                # Show context around error
                $lines = $logs -split "`n"
                for ($i = 0; $i -lt $lines.Count; $i++) {
                    if ($lines[$i] -match $pattern) {
                        Write-Status "--- Error context ---" "Yellow"
                        for ($j = [Math]::Max(0, $i-3); $j -le [Math]::Min($lines.Count-1, $i+3); $j++) {
                            $color = if ($j -eq $i) { "Red" } else { "Gray" }
                            Write-Status $lines[$j] $color
                        }
                        Write-Status "---------------------" "Yellow"
                    }
                }
            }
        }
        
        if (-not $foundError) {
            Write-Status "Could not identify specific error. Last 50 lines:" "Yellow"
            ($logs -split "`n") | Select-Object -Last 50 | ForEach-Object { Write-Status $_ "Gray" }
        }
        
        exit 1
    }
    elseif ($status -eq "live") {
        Write-Status "=== Deploy Successful! ===" "Green"
        
        # Test health endpoint
        $healthUrl = "$($service.service.serviceDetails.url)/health"
        Write-Status "Testing health endpoint: $healthUrl" "Yellow"
        
        try {
            $response = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 10
            Write-Status "Health check response: $($response | ConvertTo-Json)" "Green"
        } catch {
            Write-Status "Health check failed: $_" "Yellow"
        }
        
        exit 0
    }
    else {
        Write-Status "Deploy is in progress... Check again later." "Yellow"
        exit 0
    }
    
} catch {
    Write-Status "Error: $_" "Red"
    exit 1
}
