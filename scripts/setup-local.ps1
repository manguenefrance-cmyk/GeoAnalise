$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    py -3.13 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.13 is required.' }
}
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.lock.txt
if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
Set-Location -LiteralPath (Join-Path $projectRoot 'apps\web')
npm ci --no-fund --no-audit
if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
Set-Location -LiteralPath $projectRoot
Write-Host 'Setup complete. Run .\scripts\start-local.ps1'
