param(
    [ValidateNotNullOrEmpty()]
    [parameter(Mandatory=$true, ParameterSetName='User')]
    [string]$User,

    [ValidateNotNullOrEmpty()]
    [parameter(Mandatory=$true, ParameterSetName='UserUnhashed')]
    [string]$UserUnhashed
)
try {
    Import-Module Set-PsEnv
    
    Set-PsEnv
    
    Write-Host "Server URL: $Env:SERVER_URL"
    if ($PSCmdlet.ParameterSetName -eq 'User') {
        $response = Invoke-RestMethod -Uri "$Env:SERVER_URL/get_balance?user=$User" `
            -Method 'Get' | ConvertTo-Json
        Write-Host $response
    } else {
        $response = Invoke-RestMethod -Uri "$Env:SERVER_URL/get_balance?user_unhashed=$UserUnhashed" `
            -Method 'Get' | ConvertTo-Json -Depth 10
        Write-Host $response    
    }
}
catch {
    Write-Host "Failed to get balance."
    Write-Host $_
    Pause
}