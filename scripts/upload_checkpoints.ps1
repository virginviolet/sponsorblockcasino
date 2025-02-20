try {
    Write-Warning "This script will replace checkpoints on the server."
    Pause
    Import-Module Set-PsEnv

    Set-PsEnv

    # Create zip file with the slot machine configuration
    $scriptDirPath = Split-Path -Parent $MyInvocation.MyCommand.Path
    $botDirPath = Split-Path -Parent $scriptDirPath
    $checkpointsDirPath = "$botDirPath\data\checkpoints"
    $zipFilePath = Join-Path -Path $scriptDirPath -ChildPath 'checkpoints.zip'
    $zipFilExists = Test-Path -Path $zipFilePath
    if ($zipFilExists) {
        Write-Host "Will use existing checkpoints.zip file."
        Pause
    } else {
        Pause
        Compress-Archive -Path $checkpointsDirPath -DestinationPath $zipFilePath
    }
    Write-Host "Server URL: $Env:SERVER_URL"
    Invoke-RestMethod -Uri "$Env:SERVER_URL/upload_checkpoints" `
        -Method 'Post' `
        -Headers @{ 'token' = $Env:SERVER_TOKEN } `
        -ContentType 'multipart/form-data' `
        -InFile $zipFilePath

} catch {
    Write-Host "Failed to upload checkpoints."
    Write-Host $_
    Pause
}