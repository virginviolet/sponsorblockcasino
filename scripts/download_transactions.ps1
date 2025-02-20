try {
    Import-Module Set-PsEnv
    
    Set-PsEnv
    
    Write-Host "Server URL: $Env:SERVER_URL"
    Invoke-RestMethod -Uri "$Env:SERVER_URL/download_transactions" `
        -Method 'Get' `
        -OutFile "transactions.tsv"
}
catch {
    Write-Host "Failed to download transactions."
    Write-Host $_
    Pause
}