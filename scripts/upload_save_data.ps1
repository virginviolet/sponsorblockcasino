try {
    Write-Warning "This script will replace save data on the server."
    Import-Module Set-PsEnv

    Set-PsEnv

    # Create zip file with the slot machine configuration
    $scriptDirPath = Split-Path -Parent $MyInvocation.MyCommand.Path
    $botDirPath = Split-Path -Parent $scriptDirPath
    $saveDataDirPath = "$botDirPath\data\save_data"
    $zipFilePath = Join-Path -Path $scriptDirPath -ChildPath 'save_data.zip'
    $zipFilExists = Test-Path -Path $zipFilePath
    if ($zipFilExists) {
        Write-Host "Will use existing save_data.zip file."
        Pause
    } else {
        Pause
        Compress-Archive -Path $saveDataDirPath -DestinationPath $zipFilePath
    }
    Write-Host "Server URL: $Env:SERVER_URL"
    Invoke-RestMethod -Uri "$Env:SERVER_URL/upload_save_data" `
        -Method 'Post' `
        -Headers @{ 'token' = $Env:SERVER_TOKEN } `
        -ContentType 'multipart/form-data' `
        -InFile $zipFilePath

} catch {
    Write-Host "Failed to upload checkpoints."
    Write-Host $_
    Pause
}