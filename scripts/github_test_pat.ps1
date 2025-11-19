Write-Host 'Enter GitHub PAT (input hidden):'
$sec = Read-Host -AsSecureString
$bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
$pat = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
[System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)

$headers = @{ Authorization = "token $pat"; Accept = 'application/vnd.github+json' }
try {
    $r = Invoke-RestMethod -Method Get -Uri "https://api.github.com/repos/AD-Thiago/temporal-poc/actions/workflows" -Headers $headers -ErrorAction Stop
    Write-Host "Workflows count: $($r.total_count)"
    foreach ($w in $r.workflows) { Write-Host ("{0} -> {1}" -f $w.name, $w.path) }
} catch {
    if ($_.Exception.Response) {
        $resp = $_.Exception.Response
        Write-Host "HTTP status: $($resp.StatusCode)"
        try { $body = (New-Object System.IO.StreamReader($resp.GetResponseStream())).ReadToEnd(); Write-Host "Body: $body" } catch {}
    }
    Write-Host "Error: $($_.Exception.Message)"
}
