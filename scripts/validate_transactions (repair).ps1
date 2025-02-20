try {
    Import-Module Set-PsEnv
    
    Set-PsEnv
    Write-Warning "This script might alter the transactions file."
    Read-Host -Prompt "Press Enter to continue"
    Write-Host "Server URL: $Env:SERVER_URL"
    $response = Invoke-RestMethod -Uri "$Env:SERVER_URL/validate_transactions?repair=true" `
        -Header @{'token' = $Env:SERVER_TOKEN } `
        -Method 'Get' | ConvertTo-Json
    Write-Host $response
} catch {
    Write-Host "Failed to validate."
    Write-Host $_
} finally {
    Read-Host -Prompt "Press Enter to exit"
}