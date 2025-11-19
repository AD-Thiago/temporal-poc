PAT storage (local, encrypted)
--------------------------------

This repository includes two small PowerShell helpers to securely store and retrieve a GitHub Personal Access Token (PAT) for local scripted use.

Files
- `scripts/save_github_pat.ps1`: prompts for the PAT and saves it encrypted to `%USERPROFILE%\.temporal-poc\github_pat.sec` using Windows DPAPI (ConvertFrom-SecureString). No admin rights required. The file is user-scoped: only the same Windows account can decrypt it.
- `scripts/get_github_pat.ps1`: reads the encrypted file and prints the plaintext PAT to stdout (used by automation scripts that need the token).

How it works
- The PAT is never stored in plaintext on disk. ConvertFrom-SecureString uses the Windows Data Protection API, which ties the encrypted blob to the current user profile.
- Any process running as your user can decrypt it; processes running as other users cannot.

Usage examples
1) Save the PAT (run once):
```powershell
.\scripts\save_github_pat.ps1
# enter the PAT when prompted
```

2) Retrieve the PAT in a script (example to call the dispatch script):
```powershell
$pat = & .\scripts\get_github_pat.ps1
# use $pat where needed (avoid printing it to logs)
```

Security notes
- This method is more secure than storing the PAT in plaintext, but the token can be decrypted by any process running under your user account. Do not run untrusted code under this account.
- To remove the stored token: `Remove-Item "$env:USERPROFILE\.temporal-poc\github_pat.sec" -Force`

If you want, I can run `save_github_pat.ps1` now and you can paste the PAT once; after that I will use `get_github_pat.ps1` automatically when I need the token.
