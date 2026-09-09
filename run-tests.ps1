$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " DEVDELIVERY - TESTES AUTOMATICOS" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

$testExitCode = 1

try {
Write-Host "[1/5] Configurando ambiente de teste..." -ForegroundColor Yellow

$env:DEVDELIVERY_ENV = "test"
$env:PYTHONPATH = Join-Path $PSScriptRoot "backend"

Write-Host "Ambiente: TEST" -ForegroundColor Green
Write-Host "Arquivo: backend/.env.test" -ForegroundColor Green
Write-Host ""

Write-Host "[2/5] Subindo PostgreSQL..." -ForegroundColor Yellow

docker compose up -d db

if ($LASTEXITCODE -ne 0) {
    throw "Nao foi possivel iniciar o PostgreSQL."
}

Write-Host "Aguardando PostgreSQL ficar disponivel..." -ForegroundColor Yellow

$maxAttempts = 30
$attempt = 0
$databaseReady = $false

while ($attempt -lt $maxAttempts) {
    $attempt++

    docker compose exec -T db pg_isready -U postgres 2>$null

    if ($LASTEXITCODE -eq 0) {
        $databaseReady = $true
        break
    }

    Write-Host "Tentativa $attempt/$maxAttempts..." -ForegroundColor DarkGray

    Start-Sleep -Seconds 1
}

if (-not $databaseReady) {
    throw "PostgreSQL nao ficou disponivel."
}

Write-Host "PostgreSQL esta disponivel." -ForegroundColor Green
Write-Host ""

Write-Host "[3/5] Executando migrations no banco de TESTE..." -ForegroundColor Yellow

python -m alembic upgrade head

if ($LASTEXITCODE -ne 0) {
    throw "As migrations falharam."
}

Write-Host "Migrations concluidas com sucesso." -ForegroundColor Green
Write-Host ""

Write-Host "[4/5] Executando testes..." -ForegroundColor Yellow
Write-Host ""

python -m pytest backend/tests/ -v

$testExitCode = $LASTEXITCODE

Write-Host ""

if ($testExitCode -eq 0) {
    Write-Host "============================================" -ForegroundColor Green
    Write-Host "       TODOS OS TESTES PASSARAM!" -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Green
}
else {
    Write-Host "============================================" -ForegroundColor Red
    Write-Host "       ALGUNS TESTES FALHARAM!" -ForegroundColor Red
    Write-Host "============================================" -ForegroundColor Red
}

}
catch {
Write-Host ""
Write-Host "============================================" -ForegroundColor Red
Write-Host "ERRO DURANTE A EXECUCAO DOS TESTES" -ForegroundColor Red
Write-Host "============================================" -ForegroundColor Red
Write-Host ""
Write-Host $_.Exception.Message -ForegroundColor Red

$testExitCode = 1

}
finally {
Write-Host ""
Write-Host "[5/5] Encerrando PostgreSQL..." -ForegroundColor Yellow

docker compose stop db

if ($LASTEXITCODE -eq 0) {
    Write-Host "PostgreSQL encerrado." -ForegroundColor Green
}
else {
    Write-Host "Aviso: nao foi possivel encerrar o PostgreSQL." -ForegroundColor Yellow
}

Remove-Item Env:DEVDELIVERY_ENV -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "       EXECUCAO FINALIZADA" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

}

exit $testExitCode