param(
    [string]$data
)
try {
    Import-Module Set-PsEnv
    
    Set-PsEnv
    
    Write-Host "Server URL: $Env:SERVER_URL"
    Invoke-RestMethod -Uri "$Env:SERVER_URL/add_block" `
        -Method 'Post' `
        -Headers @{'token' = $Env:SERVER_TOKEN} `
        -ContentType 'application/json' `
        -Body $data
}
catch {
    Write-Host "Failed to add block."
    Write-Host $_
    Pause
}