$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$downloads = Join-Path $env:USERPROFILE "Downloads"
$credentialsPath = Join-Path $projectRoot "credentials.json"
$python = "D:\AI\venvs\ai-agent\Scripts\python.exe"
$brave = "C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"

$urls = @(
    "https://console.cloud.google.com/apis/library/gmail.googleapis.com",
    "https://console.cloud.google.com/apis/library/calendar-json.googleapis.com",
    "https://console.cloud.google.com/apis/library/drive.googleapis.com",
    "https://console.cloud.google.com/apis/credentials"
)

if (Test-Path -LiteralPath $brave) {
    foreach ($url in $urls) {
        Start-Process -FilePath $brave -ArgumentList $url
    }
} else {
    foreach ($url in $urls) {
        Start-Process $url
    }
}

Write-Host ""
Write-Host "Opened Google Cloud setup pages."
Write-Host "Create or select a project, enable Gmail/Calendar/Drive APIs, then create OAuth Client ID -> Desktop app."
Write-Host "Download the client JSON. This script will watch Downloads and copy it to:"
Write-Host "  $credentialsPath"
Write-Host ""

$deadline = (Get-Date).AddMinutes(20)
$candidate = $null
while ((Get-Date) -lt $deadline) {
    $candidate = Get-ChildItem -LiteralPath $downloads -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match '^(client_secret|credentials).+\.json$|^credentials\.json$' } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if ($candidate -and $candidate.LastWriteTime -gt (Get-Date).AddHours(-2)) {
        break
    }

    Start-Sleep -Seconds 5
}

if (-not $candidate) {
    throw "No recent OAuth client JSON found in $downloads within 20 minutes."
}

Copy-Item -LiteralPath $candidate.FullName -Destination $credentialsPath -Force
Write-Host "Copied OAuth client JSON from:"
Write-Host "  $($candidate.FullName)"

if (-not (Test-Path -LiteralPath $python)) {
    & (Join-Path $projectRoot "run_assistant.ps1")
}

Set-Location $projectRoot
& $python get_google_service.py
& $python setup_check.py
