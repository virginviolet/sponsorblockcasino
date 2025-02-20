try {
    Import-Module Set-PsEnv
    
    Set-PsEnv
    Write-Host "Server URL: $Env:SERVER_URL"
    Write-Warning "The server will shut down."
    Pause
    Invoke-RestMethod -Uri "$Env:SERVER_URL/shutdown" `
        -Method 'Post' `
        -Headers @{'token' = $Env:SERVER_TOKEN} `
}
catch {
    Write-Host "Failed to shutdown server."
    Write-Host $_
    Pause
}