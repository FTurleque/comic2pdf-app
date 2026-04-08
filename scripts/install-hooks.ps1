# scripts/install-hooks.ps1
# Installation des Git hooks locaux pour comic2pdf-app (Windows PowerShell)
#
# Usage : .\scripts\install-hooks.ps1
# Prérequis : Python 3.12, Git for Windows

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot

Write-Host ""
Write-Host "=== Installation des Git hooks — comic2pdf-app ===" -ForegroundColor Cyan

# 1. Installer pre-commit
Write-Host "`n[1/4] Installation de pre-commit..." -ForegroundColor Yellow
pip install --quiet pre-commit
if ($LASTEXITCODE -ne 0) { Write-Error "Échec installation pre-commit"; exit 1 }
Write-Host "      ✓ pre-commit installé" -ForegroundColor Green

# 2. Installer les hooks pre-commit (pre-commit + commit-msg stages)
Write-Host "`n[2/4] Installation des hooks pre-commit..." -ForegroundColor Yellow
Push-Location $RepoRoot
pre-commit install
pre-commit install --hook-type commit-msg
Pop-Location
Write-Host "      ✓ Hooks pre-commit installés (commit + commit-msg)" -ForegroundColor Green

# 3. Copier le hook pre-push dans .git/hooks/
Write-Host "`n[3/4] Installation du hook pre-push..." -ForegroundColor Yellow
$src  = Join-Path $RepoRoot ".github\hooks\pre-push"
$dest = Join-Path $RepoRoot ".git\hooks\pre-push"
Copy-Item -Path $src -Destination $dest -Force
Write-Host "      ✓ Hook pre-push copié dans .git/hooks/" -ForegroundColor Green

# 4. Vérification
Write-Host "`n[4/4] Vérification..." -ForegroundColor Yellow
$hooks = @("pre-commit", "commit-msg", "pre-push")
foreach ($hook in $hooks) {
    $hookPath = Join-Path $RepoRoot ".git\hooks\$hook"
    if (Test-Path $hookPath) {
        Write-Host "      ✓ .git/hooks/$hook" -ForegroundColor Green
    } else {
        Write-Warning "      ✗ .git/hooks/$hook manquant"
    }
}

Write-Host ""
Write-Host "=== Hooks installés avec succès ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "  • pre-commit  : black --check, flake8, trailing-whitespace, check-yaml"
Write-Host "  • commit-msg  : validation Conventional Commits"
Write-Host "  • pre-push    : pytest sur les services Python modifiés"
Write-Host ""
Write-Host "  Ignorer ponctuellement : git commit --no-verify / git push --no-verify"
Write-Host ""
