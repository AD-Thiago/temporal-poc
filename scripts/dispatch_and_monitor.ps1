<#
.SYNOPSIS
  Dispatch a GitHub Actions workflow and monitor it with clear progress and logging.

.DESCRIPTION
  Use this script to dispatch a workflow (API), poll its status with timestamps,
  show progress, and automatically download + extract job logs when the run fails.

.USAGE
  # Use saved PAT (saved with save_github_pat.ps1)
  .\scripts\dispatch_and_monitor.ps1 -Owner AD-Thiago -Repo temporal-poc -Workflow cloud-run-deploy.yml -UseSavedPat

  # Or prompt for PAT interactively
  .\scripts\dispatch_and_monitor.ps1 -Owner AD-Thiago -Repo temporal-poc -Workflow cloud-run-deploy.yml -PromptForPat

REMARKS
  - Requires `get_github_pat.ps1` in the same `scripts` folder if using -UseSavedPat.
  - Downloads job logs to `.
un_logs_<runId>` when the run fails.
#>

param(
  [Parameter(Mandatory=$true)][string]$Owner,
  [Parameter(Mandatory=$true)][string]$Repo,
  [Parameter(Mandatory=$true)][string]$Workflow,
  [string]$Ref = 'main',
  [int]$PollSeconds = 5,
  [int]$TimeoutSeconds = 600,
  [switch]$UseSavedPat,
  [switch]$PromptForPat
)

function Write-Log { param($m) $ts = (Get-Date).ToString('s'); Write-Host "[$ts] $m" }

function Get-Pat {
  if ($UseSavedPat) {
    $pat = & "$PSScriptRoot\get_github_pat.ps1" 2>$null
    if (-not $pat) { throw "Failed to retrieve saved PAT. Run scripts/save_github_pat.ps1 first or use -PromptForPat." }
    return $pat.Trim()
  }
  if ($PromptForPat) {
    Write-Host "Enter GitHub PAT (input hidden):"
    $sec = Read-Host -AsSecureString
    $bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
    $plain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
    [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    return $plain
  }
  throw "No PAT source selected. Use -UseSavedPat or -PromptForPat."
}

function Invoke-Api {
  param($Method, $Url, $Headers, $Body)
  try {
    if ($Body) { return Invoke-RestMethod -Method $Method -Uri $Url -Headers $Headers -Body ($Body | ConvertTo-Json) -ContentType 'application/json' -ErrorAction Stop }
    else { return Invoke-RestMethod -Method $Method -Uri $Url -Headers $Headers -ErrorAction Stop }
  } catch {
    throw $_
  }
}

function Dispatch-Workflow {
  param($pat)
  $url = "https://api.github.com/repos/$Owner/$Repo/actions/workflows/$Workflow/dispatches"
  $headers = @{ Authorization = "token $pat"; Accept = 'application/vnd.github+json' }
  Write-Log "Dispatching workflow $Workflow -> $Owner/$Repo@$Ref"
  try {
    $body = @{ ref = $Ref }
    $json = $body | ConvertTo-Json
    Invoke-RestMethod -Method Post -Uri $url -Headers $headers -Body $json -ContentType 'application/json' -ErrorAction Stop | Out-Null
    Write-Log "Dispatch request accepted (expected 204 No Content)."
  } catch {
    Write-Log "Dispatch error: $($_.Exception.Message)"
    throw $_
  }
}

function Find-RecentRun {
  param($pat)
  $url = "https://api.github.com/repos/$Owner/$Repo/actions/runs?per_page=50"
  $headers = @{ Authorization = "token $pat"; Accept = 'application/vnd.github+json' }
  $resp = Invoke-Api -Method Get -Url $url -Headers $headers
  foreach ($run in $resp.workflow_runs) {
    if ($run.head_branch -eq $Ref -or $run.head_branch -eq ($Ref -replace 'refs/heads/','')) {
      # consider recent runs (last 5 min)
      $created = [datetime]::Parse($run.created_at)
      if ((Get-Date) - $created -lt (New-TimeSpan -Minutes 5)) { return $run }
    }
  }
  return $null
}

function Monitor-Run {
  param($pat, $runId)
  $runUrl = "https://api.github.com/repos/$Owner/$Repo/actions/runs/$runId"
  $headers = @{ Authorization = "token $pat"; Accept = 'application/vnd.github+json' }
  $t0 = Get-Date
  while ((Get-Date) - $t0 -lt (New-TimeSpan -Seconds $TimeoutSeconds)) {
    $r = Invoke-Api -Method Get -Url $runUrl -Headers $headers
    $status = $r.status
    $conclusion = $r.conclusion
    $msg = "Run $runId status=$status conclusion=$conclusion"
    Write-Log $msg
    Write-Progress -Activity "Monitoring workflow run" -Status $msg -PercentComplete ([math]::Min(100, ((Get-Date) - $t0).TotalSeconds / $TimeoutSeconds * 100))
    if ($status -eq 'completed') { return $r }
    Start-Sleep -Seconds $PollSeconds
  }
  throw "Timeout waiting for run $runId to complete"
}

function Download-And-Inspect-Logs {
  param($pat, $jobId, $outDir)
  $logsUrl = "https://api.github.com/repos/$Owner/$Repo/actions/jobs/$jobId/logs"
  $headers = @{ Authorization = "token $pat" }
  $tmpLog = Join-Path $outDir "job_${jobId}_logs.txt"
  Write-Log "Downloading logs for job $jobId"
  try {
    Invoke-WebRequest -Uri $logsUrl -Headers $headers -OutFile $tmpLog -ErrorAction Stop
    Write-Log "Downloaded logs to: $tmpLog"
    # search for error markers
    $txt = Get-Content -Raw -Path $tmpLog -ErrorAction SilentlyContinue
    $pattern = 'ERROR|Error|failed|FAILURE|Traceback'
    if ($txt -match $pattern) {
      Write-Log "---- Error markers found in log:"
      $lines = $txt -split "`n"
      $snippet = $lines[0..[math]::Min(200, $lines.Length-1)] -join "`n"
      Write-Host $snippet
      Write-Log "---- end snippet"
    } else {
      Write-Log "No error markers found. Full log saved at: $tmpLog"
    }
  } catch {
    Write-Log "Failed to download logs: $($_.Exception.Message)"
  }
}

try {
  $pat = Get-Pat
  Dispatch-Workflow -pat $pat

  # find the created run
  $found = $null
  $t0 = Get-Date
  while ((Get-Date) - $t0 -lt (New-TimeSpan -Seconds 60)) {
    $found = Find-RecentRun -pat $pat
    if ($found) { break }
    Start-Sleep -Seconds 2
  }
  if (-not $found) { throw "No recent run found after dispatch" }
  $runId = $found.id
  Write-Log "Found run id=$runId url=$($found.html_url)"

  $runObj = Monitor-Run -pat $pat -runId $runId
  if ($runObj.conclusion -ne 'success') {
    Write-Log "Run concluded with: $($runObj.conclusion). Downloading job logs for inspection."
    $jobsUrl = "https://api.github.com/repos/$Owner/$Repo/actions/runs/$runId/jobs"
    $jobs = Invoke-Api -Method Get -Url $jobsUrl -Headers @{ Authorization = "token $pat"; Accept = 'application/vnd.github+json' }
    $outDir = Join-Path $PSScriptRoot "run_logs_$runId"
    if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir | Out-Null }
    foreach ($job in $jobs.jobs) {
      if ($job.conclusion -ne 'success') { Download-And-Inspect-Logs -pat $pat -jobId $job.id -outDir $outDir }
    }
    Write-Log "Logs downloaded to: $outDir"
    exit 1
  } else {
    Write-Log "Run succeeded. URL: $($runObj.html_url)"
  }
} catch {
  Write-Log "ERROR: $($_.Exception.Message)"
  exit 2
}
