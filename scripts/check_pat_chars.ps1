$p=Join-Path $env:USERPROFILE '.temporal-poc\\github_pat.sec'
if (-not (Test-Path $p)) { Write-Host "PAT file not found: $p"; exit 1 }
$s=Get-Content -Raw -Path $p -Encoding UTF8
# Remove expected characters and see what's left
$bad = ($s -replace '[0-9A-Fa-f\-,\s]','')
Write-Host "Bad chars count: $($bad.Length)"
if ($bad.Length -gt 0) {
    Write-Host "First bad characters and codes:"
    $max = [math]::Min(20, $bad.Length)
    for ($i=0;$i -lt $max; $i++) {
        $ch = $bad[$i]
        Write-Host ("'{0}' ({1})" -f $ch, ([int][char]$ch))
    }
}
Write-Host ('Checked length: ' + $s.Length)
