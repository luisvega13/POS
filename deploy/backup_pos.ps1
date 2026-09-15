$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $PSScriptRoot
$Source = Join-Path $ProjectDir "data\pos.db"
$BackupDir = Join-Path $ProjectDir "backups"
if (-not (Test-Path -LiteralPath $Source)) { throw "No existe data\pos.db" }
New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$Destination = Join-Path $BackupDir "pos-$Stamp.db"
Copy-Item -LiteralPath $Source -Destination $Destination
Write-Host "Respaldo creado: $Destination"
