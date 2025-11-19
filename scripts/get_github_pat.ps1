<#: 
.SYNOPSIS
  Retrieve the stored GitHub PAT (decrypts the file saved by `save_github_pat.ps1`).

.DESCRIPTION
  Reads the encrypted token file in `%USERPROFILE%\.temporal-poc\github_pat.sec`,
  converts it back to a SecureString and writes the plaintext PAT to stdout.

.NOTES
  The file is encrypted with DPAPI and can only be decrypted by the same Windows user account.
#>

param(
  [string]$InPath = "$env:USERPROFILE\.temporal-poc\github_pat.sec"
)

if (-not (Test-Path -Path $InPath)) {
    Write-Error "PAT file not found at: $InPath"
    exit 1
}

$enc = Get-Content -Raw -Path $InPath -Encoding UTF8
$secure = ConvertTo-SecureString $enc

# Convert SecureString to plaintext (for scripts that need the token)
$ptr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
$plain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($ptr)
[System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)

Write-Output $plain
