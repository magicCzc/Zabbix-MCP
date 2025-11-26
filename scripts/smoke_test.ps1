# Copyright (c) 2025 Zabbix-MCP
# Licensed under the Apache License, Version 2.0

param(
  [string]$EnvFile = ".env",
  [string]$BaseUrl = "http://127.0.0.1:5656"
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

Load-DotEnv $EnvFile
$read = $env:MCP_AUTH_TOKEN_READ
$admin = $env:MCP_AUTH_TOKEN_ADMIN

if (-not (Test-Path "logs")) { New-Item -ItemType Directory -Path "logs" | Out-Null }
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$Report = Join-Path "logs" ("smoke_" + $ts + ".log")

function CallGet($path, $token) {
  $sw = [System.Diagnostics.Stopwatch]::StartNew()
  try {
    $res = Invoke-RestMethod -Method Get -Uri ($BaseUrl + $path) -Headers @{ Authorization = "Bearer $token" }
    $sw.Stop()
    $line = "GET {0} 200 {1}ms" -f $path, [int]$sw.Elapsed.TotalMilliseconds
    $line | Tee-Object -FilePath $Report -Append
  } catch {
    $sw.Stop()
    $status = "ERR"
    try { $status = $_.Exception.Response.StatusCode.value__ } catch {}
    ("GET {0} {1} {2}ms" -f $path, $status, [int]$sw.Elapsed.TotalMilliseconds) | Tee-Object -FilePath $Report -Append
  }
}

function CallPost($path, $body, $token) {
  $sw = [System.Diagnostics.Stopwatch]::StartNew()
  try {
    $res = Invoke-RestMethod -Method Post -Uri ($BaseUrl + $path) -Headers @{ Authorization = "Bearer $token" } -Body $body -ContentType 'application/json'
    $sw.Stop()
    $line = "POST {0} 200 {1}ms" -f $path, [int]$sw.Elapsed.TotalMilliseconds
    $line | Tee-Object -FilePath $Report -Append
  } catch {
    $sw.Stop()
    $status = "ERR"
    try { $status = $_.Exception.Response.StatusCode.value__ } catch {}
    ("POST {0} {1} {2}ms" -f $path, $status, [int]$sw.Elapsed.TotalMilliseconds) | Tee-Object -FilePath $Report -Append
  }
}

# Read endpoints
CallGet "/health" $read
CallGet "/metrics" $read
CallGet "/version" $read
CallGet "/alerts/today?limit=5" $read
CallGet "/alerts/top?by=severity&limit=5" $read

$q1 = @{ severities=@(4); limit=5 } | ConvertTo-Json
CallPost "/alerts/query" $q1 $read

$nl = @{ text="today top5 by severity" } | ConvertTo-Json
$nlPath = "/alerts/nl"
CallPost $nlPath $nl $read

$logsReq = @{ keywords=@("Processor","load"); limit=5 } | ConvertTo-Json
CallPost "/logs/associate" $logsReq $read

# Admin endpoints should be forbidden in READ_ONLY
$empty = "{}"
CallPost "/config/reload" $empty $admin
CallPost "/queue/enqueue" $empty $admin
CallGet "/queue/stats" $admin
