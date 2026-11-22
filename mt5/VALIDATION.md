# Validar a engine no Strategy Tester do MT5

Objetivo: rodar a mesma estratégia no MT5 e comparar com `engine/validation/SUMMARY.md`
e com os CSVs de trades em `engine/validation/`.

## 1. Preparar
1. Copie `mt5/EngineStrategy.mq5` para `MQL5/Experts` e compile no MetaEditor (F7).
2. Em `engine/config/symbols.json`, coloque os dados reais da sua corretora (botão direito no símbolo >
   Especificação): tamanho do contrato, volume mínimo e passo, comissão, swap comprado/vendido,
   dia do swap triplo, e o depósito que vai usar no teste. Confira também o fuso do servidor.
3. Rode de novo: `python -m engine.portfolio` e `python -m engine.export_trades`.

## 2. Configurar o testador (Ctrl+R)
| Campo | Valor |
|---|---|
| Expert | EngineStrategy |
| Símbolo / Período | US500 (nome da sua corretora), D1 |
| Datas | 2021.05.24 a 2026.05.22 |
| Modelagem | Cada tick baseado em ticks reais |
| Atrasos | Sem atraso (compara com as linhas "tester") |
| Depósito / Alavancagem | 10000 USD (igual ao `initial_deposit`), 1:100 |
| Parâmetros | os da coluna "EA inputs" do `SUMMARY.md` |

Combo principal (regras ao pé da letra):
`Strategy=RSI_REVERSION; Exposure=1.0; RsiPeriod=2; RsiBuyBelow=10; RsiExitAbove=50`

## 3. Comparar
| No relatório do MT5 | Na engine (`SUMMARY.md`, linha "tester") |
|---|---|
| Total de negociações | Trades |
| Lucro líquido total | Net profit |
| Rebaixamento máximo do capital líquido (%) | Max DD % |
| Fator de lucro | Profit factor |
| Lista de ordens (data de entrada/saída, volume, preço) | CSV `..._tester.csv` |

## 4. Diferenças esperadas
- **Datas de entrada e saída devem coincidir** na grande maioria dos trades. Se quase todas estiverem
  deslocadas, o fuso do servidor em `symbols.json` não é o da corretora.
- **Preços** diferem um pouco: os ticks da engine são da Dukascopy, os do MT5 são da corretora.
- **Lucro** difere pelo swap e pela comissão reais da corretora, e pelo histórico de ticks dela
  (se a corretora não tiver ticks reais de 2021, o MT5 gera ticks e a qualidade cai; veja a
  "Qualidade do histórico" no relatório).
- O RSI do MT5 e o da engine usam a mesma suavização; diferenças só nas primeiras barras.

Mande o relatório do MT5 (HTML ou XML) e a especificação do símbolo para ajustar o que divergir.
