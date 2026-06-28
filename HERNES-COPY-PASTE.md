# Backtest no MT4 via PowerShell / .BAT — guia rápido

**O que é:** o `terminal.exe` do MT4 aceita um arquivo `.ini` com a seção
`[Tester]`. Ele abre, roda o backtest sozinho, salva um relatório `.htm` e fecha.
O `.bat`/PowerShell só dispara isso — e em loop roda vários testes seguidos.

## Antes de começar (anote 3 coisas)
1. **Caminho do `terminal.exe`** (ex.: `C:\Program Files (x86)\MetaTrader 4\terminal.exe`)
2. **Nome EXATO do EA** (como aparece no Navigator, sem `.ex4`)
3. **Nome EXATO do símbolo** (igual ao Market Watch do broker: `EURUSD`, `XAUUSD`...)

> Tenha também o **histórico de preços baixado** para o símbolo/período — o tester
> não baixa sozinho.

## Passo 1 — crie `backtest.ini`
```ini
[Tester]
TestExpert=Moving Average          ; EDITAR: nome exato do EA (sem .ex4)
TestSymbol=EURUSD                  ; EDITAR: simbolo exato do broker
TestPeriod=H1                      ; M1 M5 M15 M30 H1 H4 D1 W1 MN
TestModel=0                        ; 0=Every tick 1=Control points 2=Open prices
TestOptimization=false
TestDateEnable=true
TestFromDate=2023.01.01            ; EDITAR data inicial (AAAA.MM.DD)
TestToDate=2023.12.31              ; EDITAR data final
TestReport=tester\rel_EURUSD       ; relatorio .htm na pasta do MT4
TestReplaceReport=true
TestShutdownTerminal=true          ; ESSENCIAL: fecha o MT4 ao terminar
TestVisualEnable=false
; --- SO se o EA exigir conta logada, descomente: ---
; [Common]
; Login=12345678
; Password=suaSenha
; Server=SeuBroker-Server
```

> Para usar inputs salvos do EA, gere um `.set` no MT4 (Strategy Tester → Expert
> properties → Inputs → Save, na pasta `tester\`) e adicione
> `TestExpertParameters=meu.set`.

## Passo 2A — rodar UM teste (.bat)
Crie `rodar_backtest.bat`:
```bat
@echo off
set "MT4=C:\Program Files (x86)\MetaTrader 4\terminal.exe"
set "CFG=%~dp0backtest.ini"
"%MT4%" "%CFG%"
echo Concluido. Relatorio em (MT4)\tester\rel_EURUSD.htm
pause
```
Dois cliques no `.bat`.

## Passo 2B — rodar VÁRIOS em lote (PowerShell)
Crie `rodar_backtests.ps1`:
```powershell
$mt4     = "C:\Program Files (x86)\MetaTrader 4\terminal.exe"  # EDITAR
$cfgDir  = "$PSScriptRoot\cfg"
$ea      = "Moving Average"          # EDITAR: nome do EA
$periodo = "H1"
$de      = "2023.01.01"              # EDITAR
$ate     = "2023.12.31"              # EDITAR
$symbols = @("EURUSD","GBPUSD","USDJPY","XAUUSD")   # EDITAR

New-Item -ItemType Directory -Force -Path $cfgDir | Out-Null
foreach ($sym in $symbols) {
    $ini = Join-Path $cfgDir "bt_$sym.ini"
@"
[Tester]
TestExpert=$ea
TestSymbol=$sym
TestPeriod=$periodo
TestModel=0
TestOptimization=false
TestDateEnable=true
TestFromDate=$de
TestToDate=$ate
TestReport=tester\rel_$sym
TestReplaceReport=true
TestShutdownTerminal=true
TestVisualEnable=false
"@ | Set-Content -Path $ini -Encoding ASCII
    Write-Host "==> Rodando: $sym" -ForegroundColor Cyan
    Start-Process -FilePath $mt4 -ArgumentList "`"$ini`"" -Wait
    Write-Host "    OK -> tester\rel_$sym.htm" -ForegroundColor Green
}
Write-Host "Todos terminaram." -ForegroundColor Yellow
```
Rode com:
```powershell
powershell -ExecutionPolicy Bypass -File .\rodar_backtests.ps1
```
O `-Wait` espera cada MT4 fechar antes do próximo (funciona por causa do
`TestShutdownTerminal=true`).

## Onde sai o resultado
Relatórios `.htm` (+ `.gif` da curva) em `...\MetaTrader 4\tester\rel_<simbolo>.htm`.
"Terminou" = o `terminal.exe` fechou (o `-Wait` detecta).

## Tabela de parâmetros do `[Tester]`
| Chave | Função | Valores |
|---|---|---|
| `TestExpert` | nome do EA (obrigatório) | `Moving Average` |
| `TestExpertParameters` | `.set` de inputs (pasta `tester\`) | `meu.set` ou omitir |
| `TestSymbol` | símbolo exato | `EURUSD` |
| `TestPeriod` | timeframe | `M1`...`MN` |
| `TestModel` | modelo | `0`=Every tick `1`=Control points `2`=Open prices |
| `TestFromDate`/`TestToDate` | datas | `AAAA.MM.DD` |
| `TestReport` | relatório `.htm` | `tester\rel_x` |
| `TestShutdownTerminal` | fecha ao terminar | `true` |
| `TestVisualEnable` | modo visual | `false` = rápido |

## Erros comuns
| Sintoma | Solução |
|---|---|
| Abre e não testa | `TestExpert` com nome exato do EA |
| Relatório vazio | datas dentro do histórico baixado |
| MT4 não fecha | adicione `TestShutdownTerminal=true` |
| Símbolo não encontrado | use o nome exato do Market Watch |
| Script PS bloqueado | rode com `-ExecutionPolicy Bypass` |
| `.ini` ignorado | passe o caminho **absoluto** do `.ini` |

> ⚠️ **Importante:** a linha de comando deixa o processo rápido e repetível, mas
> **não** melhora a qualidade dos dados. A `Modelling Quality` (99% vs 90%)
> depende do histórico/tick data carregado no MT4 — isso é independente do script.
