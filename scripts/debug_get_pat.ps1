$p = Join-Path $env:USERPROFILE '.temporal-poc\github_pat.sec'
if (-not (Test-Path $p)) { Write-Host "PAT file not found: $p"; exit 1 }
$s = Get-Content -Raw -Path $p -Encoding UTF8
try {
    $secure = ConvertTo-SecureString $s
    $ptr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    $plain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($ptr)
    [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    Write-Host "OK: token length " + $plain.Length
} catch {
    Write-Host "ERROR MESSAGE: $($_.Exception.Message)"
    Write-Host "TYPE: $($_.Exception.GetType().FullName)"
    Write-Host "STACKTRACE: $($_.Exception.StackTrace)"
    if ($_.Exception.InnerException) { Write-Host "INNER: $($_.Exception.InnerException.Message)" }
}
