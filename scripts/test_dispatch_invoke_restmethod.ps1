Write-Host 'Enter GitHub PAT (input hidden):'
$sec = Read-Host -AsSecureString
$bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
$pat = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
[System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)

$url = "https://api.github.com/repos/AD-Thiago/temporal-poc/actions/workflows/cloud-run-deploy.yml/dispatches"
$headers = @{ Authorization = "token $pat"; Accept = 'application/vnd.github+json' }
$body = @{ ref = 'main' }
try {
    $r = Invoke-RestMethod -Method Post -Uri $url -Headers $headers -Body ($body | ConvertTo-Json) -ContentType 'application/json' -ErrorAction Stop
    Write-Host 'Invoke-RestMethod returned:'; $r
} catch {
    if ($_.Exception.Response) { $resp = $_.Exception.Response; Write-Host "HTTP status: $($resp.StatusCode)"; try { $bodyText = (New-Object System.IO.StreamReader($resp.GetResponseStream())).ReadToEnd(); Write-Host "Body: $bodyText" } catch {} }
    Write-Host "Error: $($_.Exception.Message)"
}
