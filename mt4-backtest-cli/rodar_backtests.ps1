# ============================================================
#  Roda VARIOS backtests no MT4 em lote (um por simbolo).
#  Gera um .ini para cada simbolo e roda em serie.
#
#  Executar:
#    powershell -ExecutionPolicy Bypass -File .\rodar_backtests.ps1
# ============================================================

# ---- EDITAR estes valores ----
$mt4     = "C:\Program Files (x86)\MetaTrader 4\terminal.exe"  # caminho do terminal.exe
$cfgDir  = "$PSScriptRoot\cfg"                                  # onde gravar os .ini gerados
$ea      = "Moving Average"          # nome EXATO do EA (sem .ex4)
$setFile = ""                        # arquivo .set na pasta tester\ (deixe "" p/ inputs padrao)
$periodo = "H1"                      # M1 M5 M15 M30 H1 H4 D1 W1 MN
$model   = 0                         # 0=Every tick 1=Control points 2=Open prices
$de      = "2023.01.01"              # data inicial AAAA.MM.DD
$ate     = "2023.12.31"              # data final   AAAA.MM.DD
$symbols = @("EURUSD","GBPUSD","USDJPY","XAUUSD")   # adicione quantos quiser
# --------------------------------

if (-not (Test-Path $mt4)) {
    Write-Host "ERRO: terminal.exe nao encontrado em: $mt4" -ForegroundColor Red
    Write-Host "Ajuste a variavel `$mt4 no topo do script." -ForegroundColor Red
    exit 1
}

New-Item -ItemType Directory -Force -Path $cfgDir | Out-Null

$setLine = if ($setFile) { "TestExpertParameters=$setFile" } else { "" }

foreach ($sym in $symbols) {
    $ini = Join-Path $cfgDir "bt_$sym.ini"

@"
[Tester]
TestExpert=$ea
$setLine
TestSymbol=$sym
TestPeriod=$periodo
TestModel=$model
TestOptimization=false
TestDateEnable=true
TestFromDate=$de
TestToDate=$ate
TestReport=tester\rel_$sym
TestReplaceReport=true
TestShutdownTerminal=true
TestVisualEnable=false
"@ | Set-Content -Path $ini -Encoding ASCII

    Write-Host "==> Rodando backtest: $sym" -ForegroundColor Cyan
    Start-Process -FilePath $mt4 -ArgumentList "`"$ini`"" -Wait
    Write-Host "    OK -> tester\rel_$sym.htm" -ForegroundColor Green
}

Write-Host "`nTodos os backtests terminaram." -ForegroundColor Yellow
Write-Host "Relatorios na pasta (MT4)\tester\rel_<simbolo>.htm"
