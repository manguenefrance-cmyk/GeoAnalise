param([int]$WebPort = 3000, [int]$ApiPort = 8000)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Run scripts/setup-local.ps1 first.' }
$env:APP_ENV = 'test'
$env:API_URL = "http://127.0.0.1:$ApiPort"
$env:NEXT_TELEMETRY_DISABLED = '1'
& $pythonPath -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw 'Migration failed.' }
$apiProcess = Start-Process -FilePath $pythonPath -ArgumentList '-m','uvicorn','services.api.main:app','--host','127.0.0.1','--port',$ApiPort -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru
$workerProcess = Start-Process -FilePath $pythonPath -ArgumentList '-m','services.api.jobs' -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru
Write-Host "ARCAMBE test laboratory: http://127.0.0.1:$WebPort"
Write-Host 'Keep this terminal running. Ctrl+C stops the web/API/worker.'
try {
    Set-Location -LiteralPath (Join-Path $projectRoot 'apps\web')
    npm run dev -- --port $WebPort
} finally {
    Stop-Process -Id $apiProcess.Id,$workerProcess.Id -ErrorAction SilentlyContinue
    Set-Location -LiteralPath $projectRoot
}
