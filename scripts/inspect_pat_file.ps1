$p = Join-Path $env:USERPROFILE '.temporal-poc\github_pat.sec'
if (-not (Test-Path $p)) { Write-Host "PAT file not found: $p"; exit 0 }
$s = Get-Content -Raw -Path $p -Encoding UTF8
$len = $s.Length
$head = if ($len -ge 6) { $s.Substring(0,6) } else { $s }
$tail = if ($len -ge 6) { $s.Substring($len-6) } else { $s }
Write-Host "File exists. Length: $len"
Write-Host "Head (6 chars): $head"
Write-Host "Tail (6 chars): $tail"
