# Backtest automatizado no MT4 via PowerShell / arquivo .BAT

Guia completo e autoexplicativo para rodar backtests no **MetaTrader 4** pela
**linha de comando**, sem abrir e clicar no Strategy Tester manualmente. Usa um
arquivo de configuração `.ini` chamado por um `.bat` ou por um script
**PowerShell**. Serve para rodar **um** teste ou **vários em lote**.

> **Resumo em uma frase:** o `terminal.exe` do MT4 aceita um arquivo `.ini` com
> uma seção `[Tester]`; ele abre, roda o backtest sozinho, salva um relatório
> `.htm` e fecha. O `.bat`/PowerShell só dispara isso — e em loop dá pra rodar
> dezenas de testes seguidos.

---

## 1. Como funciona (a ideia em 30 segundos)

```
 ┌──────────────┐     chama      ┌──────────────┐    lê config   ┌──────────────┐
 │ .bat / .ps1  │ ─────────────► │ terminal.exe │ ─────────────► │ backtest.ini │
 └──────────────┘                └──────┬───────┘                └──────────────┘
                                        │ roda o Strategy Tester
                                        ▼
                                 ┌──────────────┐
                                 │ tester\*.htm │  ← relatório (lucro, DD, etc.)
                                 └──────────────┘
```

1. Você descreve o teste num arquivo `.ini` (EA, símbolo, datas, modelo...).
2. O script chama `terminal.exe "caminho\backtest.ini"`.
3. Por causa de `TestShutdownTerminal=true`, o MT4 **fecha sozinho** ao terminar.
4. O relatório fica em `...\MetaTrader 4\tester\`.

---

## 2. Pré-requisitos (faça uma vez)

1. **Saber o caminho do `terminal.exe`.** Normalmente:
   `C:\Program Files (x86)\MetaTrader 4\terminal.exe`
   (ou a pasta da instalação do seu broker). Anote o caminho completo.

2. **Saber o nome EXATO do EA.** É o nome como aparece no *Navigator → Expert
   Advisors* do MT4 (ex.: `Moving Average`). Sem `.ex4` no fim.

3. **Saber o nome EXATO do símbolo.** É o nome do *Market Watch* do seu broker
   (ex.: `EURUSD`, `XAUUSD`, `XAUUSDm`, `US500`). Tem que bater 100%.

4. **(Opcional) Gerar o arquivo `.set` com os inputs do EA.**
   - Abra o MT4 → `Ctrl+R` (Strategy Tester) → selecione o EA → **Expert
     properties** → aba **Inputs** → botão **Save**.
   - Salve em `...\MetaTrader 4\tester\` com um nome, ex.: `ma.set`.
   - Se você só quer os valores padrão do EA, pode **pular** este passo.

5. **(Importante) Ter o histórico de preços baixado** para o símbolo e período
   que vai testar (o tester não baixa sozinho). Veja a seção 8.

---

## 3. O arquivo de configuração `backtest.ini`

Crie um arquivo de texto chamado `backtest.ini` (ex.: na pasta `C:\mt4cfg\`).
Conteúdo mínimo funcional:

```ini
[Tester]
TestExpert=Moving Average
TestExpertParameters=ma.set
TestSymbol=EURUSD
TestPeriod=H1
TestModel=0
TestOptimization=false
TestDateEnable=true
TestFromDate=2023.01.01
TestToDate=2023.12.31
TestReport=tester\rel_EURUSD_2023
TestReplaceReport=true
TestShutdownTerminal=true
TestVisualEnable=false
```

### Tabela de todos os parâmetros

| Chave | O que faz | Valores / exemplo |
|---|---|---|
| `TestExpert` | nome do EA a testar (**obrigatório**) | `Moving Average` |
| `TestExpertParameters` | arquivo `.set` com os inputs (pasta `tester\`) | `ma.set` (ou omitir) |
| `TestSymbol` | símbolo, nome exato do broker | `EURUSD` |
| `TestPeriod` | timeframe | `M1` `M5` `M15` `M30` `H1` `H4` `D1` `W1` `MN` |
| `TestModel` | modelo de modelagem | `0`=Every tick · `1`=Control points · `2`=Open prices |
| `TestOptimization` | liga otimização (varre parâmetros) | `true` / `false` |
| `TestDateEnable` | usar intervalo de datas | `true` / `false` |
| `TestFromDate` | data inicial | `2023.01.01` (ano.mês.dia) |
| `TestToDate` | data final | `2023.12.31` |
| `TestReport` | nome/caminho do relatório (cria `.htm`) | `tester\rel_EURUSD_2023` |
| `TestReplaceReport` | sobrescreve o relatório se já existir | `true` / `false` |
| `TestShutdownTerminal` | **fecha o MT4 ao terminar** (essencial p/ script) | `true` / `false` |
| `TestVisualEnable` | modo visual (mais lento) | `false` = rápido |

> **Datas:** o formato é **`AAAA.MM.DD`** (com pontos). Use só datas dentro do
> histórico que você tem baixado, senão o teste roda "vazio".

---

## 4. Opção A — rodar com um arquivo `.BAT` (mais simples)

Crie `rodar_backtest.bat`:

```bat
@echo off
REM === Ajuste estes 2 caminhos ===
set "MT4=C:\Program Files (x86)\MetaTrader 4\terminal.exe"
set "CFG=C:\mt4cfg\backtest.ini"

echo Iniciando backtest...
"%MT4%" "%CFG%"

echo.
echo Backtest concluido.
echo Relatorio em: ...\MetaTrader 4\tester\rel_EURUSD_2023.htm
pause
```

Dê dois cliques no `.bat` (ou rode no Prompt). O MT4 abre, roda, salva o
relatório e fecha sozinho.

---

## 5. Opção B — rodar com PowerShell (mais eficiente, roda VÁRIOS em lote)

Aqui está o ganho real: gerar **vários `.ini` automaticamente** (vários símbolos,
períodos ou datas) e rodar um atrás do outro, esperando cada um terminar.

Crie `rodar_backtests.ps1`:

```powershell
# === Ajuste estes valores ===
$mt4     = "C:\Program Files (x86)\MetaTrader 4\terminal.exe"
$cfgDir  = "C:\mt4cfg"
$ea      = "Moving Average"
$periodo = "H1"
$de      = "2023.01.01"
$ate     = "2023.12.31"
$symbols = @("EURUSD","GBPUSD","USDJPY","XAUUSD")   # adicione quantos quiser

# Garante que a pasta de configs existe
New-Item -ItemType Directory -Force -Path $cfgDir | Out-Null

foreach ($sym in $symbols) {
    $ini = Join-Path $cfgDir "bt_$sym.ini"

    # Gera o .ini deste símbolo
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

    Write-Host "==> Rodando backtest: $sym" -ForegroundColor Cyan
    Start-Process -FilePath $mt4 -ArgumentList "`"$ini`"" -Wait
    Write-Host "    OK -> tester\rel_$sym.htm" -ForegroundColor Green
}

Write-Host "`nTodos os backtests terminaram." -ForegroundColor Yellow
```

**Como executar:** abra o PowerShell na pasta do script e rode:

```powershell
powershell -ExecutionPolicy Bypass -File .\rodar_backtests.ps1
```

O `-Wait` faz o PowerShell **esperar o MT4 fechar** antes de iniciar o próximo
(funciona porque o `.ini` tem `TestShutdownTerminal=true`). Resultado: os testes
rodam **em série**, sem sobreposição, sem você tocar em nada.

---

## 6. Onde sai o resultado e como saber que terminou

- **Relatório:** `...\MetaTrader 4\tester\rel_<simbolo>.htm` (+ um `.gif` com a
  curva de saldo).
- **"Terminou" =** o processo `terminal.exe` fechou. No PowerShell, o `-Wait` já
  detecta isso automaticamente.
- Depois você pode abrir o `.htm` no navegador, ou parsear para extrair lucro,
  drawdown, profit factor, etc. (exemplo simples de leitura no PowerShell):

```powershell
$html = Get-Content "C:\Program Files (x86)\MetaTrader 4\tester\rel_EURUSD.htm" -Raw
if ($html -match "Total net profit</td>\s*<td[^>]*>([^<]+)") {
    Write-Host "Lucro liquido EURUSD: $($matches[1])"
}
```

---

## 7. Conta logada (só se o EA/símbolo exigir conexão)

Alguns símbolos/EAs precisam da conta conectada. Acrescente ao **mesmo `.ini`**:

```ini
[Common]
Login=12345678
Password=suaSenha
Server=SeuBroker-Server
```

> Não compartilhe esse `.ini` com a senha dentro. Para uso pessoal/local é ok.

---

## 8. IMPORTANTE: linha de comando NÃO melhora a qualidade dos dados

O `.ini` apenas **dispara** o Strategy Tester. A **qualidade de modelagem**
(`Modelling Quality` no relatório) continua dependendo do histórico que está
instalado no MT4:

- `TestModel=0` (Every tick) + **tick data real** → ~99% (confiável).
- `TestModel=0` só com barras M1 baixadas no History Center → ~90% (MT4
  interpola os ticks).
- `TestModel=2` (Open prices only) → rápido, mas grosseiro (só p/ pré-filtro).

Ou seja: automatizar com `.bat`/PowerShell deixa o processo **rápido e repetível**,
mas para resultado **confiável** o Hernes ainda precisa ter bom histórico/tick
data carregado no MT4 antes de rodar.

---

## 9. Erros comuns e soluções

| Sintoma | Causa | Solução |
|---|---|---|
| MT4 abre e **não testa nada** | `TestExpert` errado ou vazio | use o nome exato do EA (sem `.ex4`) |
| Relatório **vazio / poucas trades** | datas fora do histórico baixado | baixe o histórico ou ajuste `TestFromDate`/`ToDate` |
| MT4 **não fecha** ao terminar | faltou `TestShutdownTerminal=true` | adicione a linha |
| Símbolo **não encontrado** | nome diferente do broker | use o nome exato do Market Watch |
| Script PowerShell **bloqueado** | ExecutionPolicy | rode com `-ExecutionPolicy Bypass` |
| Qualidade trava em **90%** | sem tick data real | carregue tick data (assunto independente do script) |
| `.ini` não é lido | caminho relativo | passe o **caminho absoluto** do `.ini` no comando |

---

## 10. Checklist para o Hernes

- [ ] Caminho do `terminal.exe` confirmado.
- [ ] Nome do **EA** exato.
- [ ] Nome do **símbolo** exato (igual ao broker).
- [ ] `.set` salvo na pasta `tester\` (ou usando inputs padrão).
- [ ] Histórico de preços baixado para o período.
- [ ] `.ini` com `TestModel=0` e `TestShutdownTerminal=true`.
- [ ] `.bat` (1 teste) **ou** `.ps1` (vários em lote) criado.
- [ ] Rodou e o `.htm` apareceu em `tester\`.

---

### Referências

- Configuration at Startup — MetaTrader 4 Help: https://www.metatrader4.com/en/trading-platform/help/service/start_conf_file
- Starting strategy tester via command line — fórum MQL4: https://www.mql5.com/en/forum/127577
- Exemplo de `mt4-tester.ini` (projeto EA31337/EA-Tester): https://github.com/EA31337/EA-Tester/blob/master/conf/mt4-tester.ini

> Conteúdo educacional/técnico. Não é recomendação de investimento.
