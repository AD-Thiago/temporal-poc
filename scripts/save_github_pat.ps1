<#: 
.SYNOPSIS
  Save a GitHub PAT encrypted to the current user using DPAPI.

.DESCRIPTION
  Prompts for a GitHub Personal Access Token (PAT) and stores it encrypted
  (via ConvertFrom-SecureString) in the user's profile folder under
  `%USERPROFILE%\.temporal-poc\github_pat.sec`.

.NOTES
  The encrypted file can only be decrypted by the same Windows user account.
  This avoids storing the token in plaintext and doesn't require installing
  additional software or admin rights.
#>

param(
  [string]$OutDir = "$env:USERPROFILE\.temporal-poc",
  [string]$FileName = 'github_pat.sec'
)

# Ensure output directory exists
if (-not (Test-Path -Path $OutDir)) {
    New-Item -ItemType Directory -Path $OutDir | Out-Null
}

$path = Join-Path $OutDir $FileName

Write-Host "Enter GitHub PAT (it will not be echoed):"
$secure = Read-Host -AsSecureString

if (-not $secure) {
    Write-Error "No token entered. Aborting."
    exit 1
}

$enc = $secure | ConvertFrom-SecureString
Set-Content -Path $path -Value $enc -Force -Encoding UTF8

# Mark the file hidden for convenience (still readable by the user)
try {
    $attr = (Get-Item -Path $path).Attributes
    Set-ItemProperty -Path $path -Name Attributes -Value ($attr -bor [System.IO.FileAttributes]::Hidden)
} catch {
    # ignore attribute errors
}

Write-Host "PAT saved (encrypted) to: $path"
Write-Host "To remove it: Remove-Item -Path $path -Force"
