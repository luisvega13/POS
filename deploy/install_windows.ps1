param([switch]$RegisterStartup)
$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $PSScriptRoot
$VenvDir = Join-Path $ProjectDir ".venv"
$Python = Join-Path $VenvDir "Scripts\python.exe"
Set-Location -LiteralPath $ProjectDir
if (-not (Test-Path -LiteralPath $Python)) { py -3 -m venv $VenvDir }
& $Python -m pip install -r (Join-Path $ProjectDir "requirements.txt")
$FrontendDir = Join-Path $ProjectDir "frontend"
$FrontendDist = Join-Path $FrontendDir "dist\index.html"
$Pnpm = Get-Command pnpm -ErrorAction SilentlyContinue
if ($Pnpm) {
    Push-Location $FrontendDir
    & $Pnpm.Source install --frozen-lockfile
    & $Pnpm.Source build
    Pop-Location
} elseif (-not (Test-Path -LiteralPath $FrontendDist)) {
    throw "El frontend no está compilado. Instale Node.js y pnpm y ejecute pnpm build en frontend."
}
& $Python -c "from app.database import init_db; init_db(); print('Base de datos preparada')"
if ($RegisterStartup) {
    $Runner = Join-Path $ProjectDir "deploy\run_pos.ps1"
    $Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$Runner`""
    $Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
    $Settings = New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
    Register-ScheduledTask -TaskName "POS Termico 58mm" -Action $Action -Trigger $Trigger -Settings $Settings -Description "Inicia el POS local y su servicio de impresión" -Force | Out-Null
    Write-Host "Inicio automático registrado para el usuario $env:USERNAME"
}
Write-Host "Instalación lista. Inicie con: powershell -ExecutionPolicy Bypass -File deploy\run_pos.ps1"
