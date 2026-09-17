# Ensures Bitget live market sidecar is up, then starts Decis UI.
# Run from anywhere:
#   powershell -File desk/start_desk.ps1
# Or from desk/:
#   .\start_desk.ps1

$ErrorActionPreference = "Stop"
$DeskRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$IaaRoot = Split-Path -Parent $DeskRoot
$UiRoot = Join-Path $DeskRoot "decis-ui"
$QuoteUrl = "http://127.0.0.1:8788/quote?symbol=RJPMUSDT"

function Test-LiveQuotes {
  try {
    $res = Invoke-WebRequest -Uri $QuoteUrl -UseBasicParsing -TimeoutSec 6
    return $res.StatusCode -eq 200
  } catch {
    return $false
  }
}

Write-Host "Checking live market sidecar on :8788 ..."
if (-not (Test-LiveQuotes)) {
  Write-Host "Starting python desk/live_quotes.py (leave this window open for Live market)"
  Start-Process -FilePath "python" -ArgumentList "desk/live_quotes.py" -WorkingDirectory $IaaRoot -WindowStyle Minimized
  $ready = $false
  for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Seconds 1
    if (Test-LiveQuotes) {
      $ready = $true
      break
    }
  }
  if (-not $ready) {
    Write-Warning "Live quotes did not respond yet — UI will keep retrying."
  } else {
    Write-Host "Live market is up."
  }
} else {
  Write-Host "Live market already running."
}

Set-Location $UiRoot
if (-not (Test-Path "node_modules")) {
  npm install
}
npm run dev -- --host 127.0.0.1 --port 5173
