Write-Host 'Enter GitHub PAT (input hidden):'
$sec = Read-Host -AsSecureString
$bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
$pat = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
[System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)

$headers = @{ Authorization = "token $pat"; Accept = 'application/vnd.github+json' }
$uri = "https://api.github.com/repos/AD-Thiago/temporal-poc/actions/workflows/cloud-run-deploy.yml/dispatches"
$body = '{"ref":"main"}'
try {
    $resp = Invoke-WebRequest -Method Post -Uri $uri -Headers $headers -Body $body -ContentType 'application/json' -ErrorAction Stop
    Write-Host "StatusCode: $($resp.StatusCode)"
    Write-Host "StatusDescription: $($resp.StatusDescription)"
} catch {
    if ($_.Exception.Response) {
        $r = $_.Exception.Response
        Write-Host "HTTP status: $($r.StatusCode)"
        try { $bodyText = (New-Object System.IO.StreamReader($r.GetResponseStream())).ReadToEnd(); Write-Host "Body: $bodyText" } catch {}
    }
    Write-Host "Error: $($_.Exception.Message)"
}
