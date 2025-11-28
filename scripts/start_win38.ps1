# Copyright (c) 2025 Zabbix-MCP
# Licensed under the Apache License, Version 2.0

param(
  [string]$EnvFile = ".env",
  [int]$Port = 5656,
  [string]$Host = "0.0.0.0"
)

function Load-DotEnv($path) {
  if (-not (Test-Path $path)) { return }
  Get-Content $path | ForEach-Object {
    if (-not $_.StartsWith("#") -and $_.Contains("=")) {
      $k,$v = $_.Split("=",2)
      if ($k -and $v) { Set-Item -Path Env:$k -Value $v }
    }
  }
}

if (-not (Test-Path "logs")) { New-Item -ItemType Directory -Path "logs" | Out-Null }
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$LogFile = Join-Path "logs" ("service_" + $ts + ".log")

function Log($msg) { Write-Host ("[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg) }

Log "Loading env from $EnvFile"
Load-DotEnv $EnvFile

if (-not (Test-Path ".venv")) {
  if (Get-Command py -ErrorAction SilentlyContinue) { & py -3.8 -m venv .venv } else { & python -m venv .venv }
}

$venvActivate = Join-Path ".venv" "Scripts\Activate.ps1"
& $venvActivate

Log "Python version"
python --version 2>&1 | Tee-Object -FilePath $LogFile -Append

Log "Installing dependencies (pip upgrade)"
python -m pip install -U pip 2>&1 | Tee-Object -FilePath $LogFile -Append
if (Test-Path "requirements.txt") {
  Log "Installing dependencies from requirements.txt"
  python -m pip install -r requirements.txt 2>&1 | Tee-Object -FilePath $LogFile -Append
} else {
  Log "requirements.txt not found; installing project editable"
  python -m pip install -e . 2>&1 | Tee-Object -FilePath $LogFile -Append
}

Log "Starting server on $Host:$Port"
uvicorn zabbix_mcp.api:app --host $Host --port $Port 2>&1 | Tee-Object -FilePath $LogFile
