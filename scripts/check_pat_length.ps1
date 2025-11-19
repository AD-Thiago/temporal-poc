# Helper: safely check saved PAT retrieval without printing the token
try {
    $t = & "$PSScriptRoot\get_github_pat.ps1"
    if ($t) {
        Write-Host ('Token length: ' + $t.Length)
    } else {
        Write-Host 'No token retrieved'
    }
} catch {
    Write-Error "Error retrieving token: $($_.Exception.Message)"
    exit 1
}
