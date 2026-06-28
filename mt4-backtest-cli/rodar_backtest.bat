@echo off
REM ============================================================
REM  Roda UM backtest no MT4 a partir de backtest.ini
REM  Edite os 2 caminhos abaixo e de dois cliques neste arquivo.
REM ============================================================

REM <<< EDITAR: caminho do terminal.exe do seu MT4
set "MT4=C:\Program Files (x86)\MetaTrader 4\terminal.exe"

REM <<< EDITAR: caminho do arquivo de configuracao
set "CFG=%~dp0backtest.ini"

if not exist "%MT4%" (
    echo ERRO: terminal.exe nao encontrado em:
    echo   %MT4%
    echo Ajuste a variavel MT4 neste .bat
    pause
    exit /b 1
)

echo Iniciando backtest...
"%MT4%" "%CFG%"

echo.
echo Backtest concluido.
echo Relatorio em: (pasta do MT4)\tester\  (arquivo .htm definido em TestReport)
pause
