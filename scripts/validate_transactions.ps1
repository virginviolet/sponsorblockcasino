try {
    Import-Module Set-PsEnv
    
    Set-PsEnv
    
    Write-Host "Server URL: $Env:SERVER_URL"
    $response = Invoke-RestMethod -Uri "$Env:SERVER_URL/validate_transactions" `
        -Method 'Get' | ConvertTo-Json
    Write-Host $response
    Read-Host -Prompt "Press Enter to exit"
} catch {
    Write-Host "Failed to validate."
    Write-Host $_
    Read-Host -Prompt "Press Enter to exit"
}