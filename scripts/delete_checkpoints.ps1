try {
    Write-Warning "This script will delete all checkpoints on the server."
    Pause
    Import-Module Set-PsEnv
    
    Set-PsEnv
    
    Write-Host "Server URL: $Env:SERVER_URL"
    Invoke-RestMethod -Uri "$Env:SERVER_URL/delete_checkpoints" `
        -Method 'Delete' `
        -Headers @{ 'token' = $Env:SERVER_TOKEN }
}
catch {
    Write-Host "Failed to delete checkpoints."
    Write-Host $_
    Pause
}