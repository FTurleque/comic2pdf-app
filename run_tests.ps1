#Requires -Version 5.1
<#
.SYNOPSIS
    [ALIAS] Lance tous les tests du projet comic2pdf-app.

.DESCRIPTION
    Ce fichier est un alias backward-compatible.
    Il delegue entierement a scripts/test_all.ps1 (point d'entree officiel).

    Utiliser directement scripts/test_all.ps1 pour acceder a toutes les options :
      .\scripts\test_all.ps1                   -- arret au premier echec (defaut)
      .\scripts\test_all.ps1 -ContinueOnError  -- execute tout + resume final

    Tous les parametres sont transmis a scripts/test_all.ps1 via @args.

.EXAMPLE
    .\run_tests.ps1
    .\run_tests.ps1 -ContinueOnError
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "  NOTE : run_tests.ps1 est un alias -- point d'entree officiel : scripts\test_all.ps1" `
    -ForegroundColor Yellow
Write-Host ""

& "$PSScriptRoot\scripts\test_all.ps1" @args
exit $LASTEXITCODE
