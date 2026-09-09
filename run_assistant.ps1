$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$venv = "D:\AI\venvs\ai-agent"
if (-not $env:AI_AGENT_HOME) {
    $env:AI_AGENT_HOME = "D:\AI\assistant"
}
if (-not $env:AI_AGENT_WORKSPACE) {
    $env:AI_AGENT_WORKSPACE = "D:\AI\assistant\workspace"
}

New-Item -ItemType Directory -Force -Path $env:AI_AGENT_HOME, $env:AI_AGENT_WORKSPACE | Out-Null

if (-not (Test-Path -LiteralPath (Join-Path $venv "Scripts\python.exe"))) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $venv) | Out-Null
    python -m venv $venv
    & (Join-Path $venv "Scripts\python.exe") -m pip install --upgrade pip
    & (Join-Path $venv "Scripts\python.exe") -m pip install -r requirements.txt
}

& (Join-Path $venv "Scripts\python.exe") -m streamlit run gui.py
