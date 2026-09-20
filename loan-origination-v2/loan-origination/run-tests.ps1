<#
Runs all three test suites (services/api, services/agent-backend, apps/web)
in one go, from the repo root, in PowerShell:

    .\run-tests.ps1

Pass -Build first time (or after installing new deps / changing a
Dockerfile) to rebuild the images before running:

    .\run-tests.ps1 -Build

Safe to re-run any time — the "CREATE DATABASE" calls below are harmless if
the throwaway test databases already exist.
#>

param(
    [switch]$Build
)

$ErrorActionPreference = "Continue"

Write-Host "==> Making sure containers are up..." -ForegroundColor Cyan
if ($Build) {
    docker compose up -d --build api agent-backend web
} else {
    docker compose up -d api agent-backend web
}

Write-Host "==> Ensuring throwaway test databases exist..." -ForegroundColor Cyan
docker compose exec db psql -U postgres -c "CREATE DATABASE loan_origination_test;" 2>$null | Out-Null
docker compose exec db psql -U postgres -c "CREATE DATABASE agent_backend_test;" 2>$null | Out-Null

$suites = @(
    @{ Name = "services/api (54 tests)";           Cmd = { docker compose exec -e TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/loan_origination_test api pytest } },
    @{ Name = "services/agent-backend (48 tests)"; Cmd = { docker compose exec -e TEST_APP_DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/agent_backend_test agent-backend pytest } },
    @{ Name = "apps/web (20 tests)";                Cmd = { docker compose exec web npm test } }
)

$results = @()

foreach ($suite in $suites) {
    Write-Host ""
    Write-Host "==> $($suite.Name)" -ForegroundColor Cyan
    & $suite.Cmd
    $results += [PSCustomObject]@{ Name = $suite.Name; ExitCode = $LASTEXITCODE }
}

Write-Host ""
Write-Host "================ Summary ================" -ForegroundColor Cyan
$anyFailed = $false
foreach ($r in $results) {
    if ($r.ExitCode -eq 0) {
        Write-Host "PASS  $($r.Name)" -ForegroundColor Green
    } else {
        Write-Host "FAIL  $($r.Name) (exit code $($r.ExitCode))" -ForegroundColor Red
        $anyFailed = $true
    }
}

if ($anyFailed) {
    exit 1
} else {
    Write-Host ""
    Write-Host "All suites passed." -ForegroundColor Green
    exit 0
}
