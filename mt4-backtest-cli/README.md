# mt4-backtest-cli — arquivos prontos

Pacote pronto para rodar backtest no MT4 pela linha de comando. Edite só o que
está marcado com `<<< EDITAR` e rode. Guia completo:
[`../GUIA-MT4-BACKTEST-AUTOMATIZADO-CLI.md`](../GUIA-MT4-BACKTEST-AUTOMATIZADO-CLI.md).

## Arquivos

| Arquivo | Para quê |
|---|---|
| `backtest.ini` | configuração de **um** backtest (EA, símbolo, datas, modelo) |
| `rodar_backtest.bat` | roda **um** backtest usando o `backtest.ini` |
| `rodar_backtests.ps1` | roda **vários** backtests em lote (um por símbolo) |

## Uso rápido

**1 teste (.bat):**
1. Abra `backtest.ini` e edite os campos `<<< EDITAR` (EA, símbolo, datas).
2. Abra `rodar_backtest.bat` e ajuste o caminho do `terminal.exe`.
3. Dois cliques no `.bat`.

**Vários testes (PowerShell):**
1. Abra `rodar_backtests.ps1` e edite o bloco no topo (EA, símbolos, datas, caminho do MT4).
2. Rode:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\rodar_backtests.ps1
   ```

## Resultado

Relatórios `.htm` na pasta `...\MetaTrader 4\tester\` (nome definido em `TestReport`).

> Lembrete: a linha de comando automatiza o teste, mas a **qualidade dos dados**
> (99% vs 90%) depende do histórico/tick data carregado no MT4. Detalhes na
> seção 8 do guia.
