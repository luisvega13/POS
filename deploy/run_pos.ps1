$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectDir ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    throw "No existe el entorno virtual. Ejecute deploy\install_windows.ps1 primero."
}
Set-Location -LiteralPath $ProjectDir
& $Python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
