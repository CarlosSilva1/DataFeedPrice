# Guia: Backtest no MetaTrader 4 com tick data real (qualidade 99%)

Guia direto, sem rodeios, para fazer backtest **confiável** no MT4 usando dados de
tick (bid/ask reais), chegando a **99% de "Modelling Quality"**. Feito para quem
nunca fez isso e não quer errar.

> **TL;DR (a melhor solução comprovada)**
> Use **Tickstory (grátis)** para exportar tick data para o MT4 e rode o
> Strategy Tester no modelo **"Every tick"**. Isso dá 99% de qualidade — é o
> método padrão que todo mundo usa.
> Quer spread variável real e slippage? Adicione o **Tick Data Suite** (pago).
> Quer usar **exatamente este dataset** (os Parquet do repositório)? Veja o
> **Caminho B**.

---

## 1. Antes de tudo: entenda os 3 conceitos que fazem o backtest ser confiável

A maioria dos backtests no MT4 é lixo por causa de 3 erros. Acerte estes e você
está à frente de 90% das pessoas:

1. **Modelling Quality (qualidade de modelagem).** No canto do relatório do MT4
   aparece um percentual: `n%`. Só existe **um jeito** de chegar a **~99%**:
   alimentar o MT4 com **tick data real** e rodar no modelo **"Every tick"**.
   - `90%` = MT4 *inventou* os ticks a partir de barras M1 → não confie.
   - `99%` = ticks reais bid/ask → confiável.
2. **Spread.** Backtest com spread fixo mente. O ideal é **spread variável real**
   (gravado tick a tick). Isso exige o Tick Data Suite. Sem ele, use pelo menos
   um spread fixo realista (ex.: o spread médio do seu broker).
3. **Fuso horário / DST.** O tick data vem em **UTC**. O seu broker MT4 costuma
   usar GMT+2/+3. Para estratégias sensíveis a horário (abertura de mercado,
   notícias), alinhe o offset — o Tickstory/TDS deixam configurar isso na hora de
   exportar.

> Regra de ouro: **se o relatório não disser 99%, o resultado não vale.**

---

## 2. Caminho A — Tickstory + MT4 (RECOMENDADO, grátis, mais simples)

Este é o caminho com **menos chance de erro**. Os dados deste repositório vieram
exatamente daqui (Dukascopy via Tickstory), então dá para reproduzir tudo de
graça e exportar direto pro MT4, sem conversão nenhuma.

### Passo a passo

1. **Baixe e instale o Tickstory Lite** (grátis): https://tickstory.com → menu
   *Download*. Instale e abra.
2. **Baixe o tick data do símbolo:**
   - Na árvore à esquerda, abra **Dukascopy → Forex/CFD** e ache o símbolo
     (ex.: `XAUUSD` para ouro, `US500`/`USA500` para o S&P 500).
   - Clique com o botão direito → **Download** e escolha o intervalo de datas
     (ex.: 2021 → 2026). Espere baixar.
3. **Exporte para o MetaTrader 4:**
   - Botão direito no símbolo → **Export to → MetaTrader**.
   - No assistente:
     - **MetaTrader build**: selecione a pasta da sua instalação do MT4.
     - **Symbol**: o nome **exato** como aparece no Market Watch do seu broker
       (ex.: `XAUUSD`, `XAUUSDm`, `GOLD`, `US500`...). Tem que bater 100%.
     - **Timeframe**: deixe **M1** (a partir do M1 o tester gera todos os outros).
     - **Time/GMT offset + DST**: ajuste para o fuso do seu broker se a
       estratégia for sensível a horário; na dúvida, deixe o padrão.
     - Marque a opção de gerar os arquivos **.fxt** (é o que o Strategy Tester
       realmente lê) e **.hst**.
   - Conclua. O Tickstory escreve os arquivos dentro das pastas `history` e
     `tester/history` do seu MT4.
4. Vá para a **Seção 4** (configuração do Strategy Tester) e rode o teste.

> O Tickstory também consegue **abrir o MT4 já configurado** ("Launch
> MetaTrader") com os dados certos — use se quiser zero atrito.

---

## 3. Caminho B — Usar EXATAMENTE este dataset (os Parquet do repo) no MT4

Use este caminho se você quer rodar o backtest sobre **estes** arquivos (já
limpos, deduplicados, em UTC), e não baixar de novo pelo Tickstory.

O MT4 **não importa Parquet**. O fluxo é: **Parquet → CSV de tick → MT4**. O CSV
de tick é importado pelo **Tick Data Suite** (a forma comprovada de injetar tick
data customizado e ainda rodar a 99%).

### B.1 — Converter Parquet → CSV (script incluso)

Requisitos: Python 3 com `pandas` e `pyarrow`.

```bash
pip install pandas pyarrow
```

Gerar um CSV único de um intervalo:

```bash
python tools/parquet_to_mt4_csv.py --instrument XAUUSD \
    --from 2024-01-01 --to 2024-03-31 --out XAUUSD_2024Q1.csv
```

Ou um arquivo por mês (recomendado — arquivos menores, mais fácil de importar):

```bash
python tools/parquet_to_mt4_csv.py --instrument US500 \
    --from 2023-01-01 --to 2023-12-31 --out-dir ./mt4_csv --split month
```

Formato gerado (padrão MT4, datas com ponto, horário em UTC):

```
dt,bid_price,ask_price,volume
2024.01.02 00:00:00,2062.34500,2062.71200,1.00000
2024.01.02 00:00:00,2062.33500,2062.72200,1.00000
...
```

### B.2 — Importar o CSV no Tick Data Suite

1. Instale o **Tick Data Suite** (pago, ~US$ 97): https://eareview.net/tick-data-suite
   Ele inclui o **Tick Data Manager** e aplica um *patch* no MT4 que permite tick
   data real + spread variável.
2. No **Tick Data Manager**, escolha **importar dados de tick a partir de CSV**
   e aponte para o(s) CSV gerado(s) no passo B.1. Defina o símbolo com o **nome
   exato** do seu broker.
3. O TDS converte o CSV nos arquivos `.fxt`/`.hst` que o Strategy Tester usa.
4. Inicie o MT4 **pelo atalho com patch do TDS** (não o atalho normal), senão o
   tick data real não é usado.
5. Vá para a **Seção 4**.

> **Alternativa sem comprar nada (qualidade ~90%, NÃO 99%):** dá para importar o
> CSV no *History Center* do MT4 (`Tools → History Center → F2`) como barras M1 e
> rodar "Every tick". Funciona para um teste rápido, mas o MT4 vai **interpolar**
> os ticks e a qualidade fica ~90%. Para resultado sério, use tick data real
> (Caminho A ou B com TDS).

---

## 4. Configuração do Strategy Tester (a parte que todo mundo erra)

Abra o MT4 → menu **View → Strategy Tester** (`Ctrl+R`). Configure **exatamente** assim:

| Campo | Valor | Por quê |
|---|---|---|
| **Expert Advisor** | seu EA | — |
| **Symbol** | o símbolo que você exportou/importou | tem que bater com os dados |
| **Model** | **Every tick** | **única** opção que dá 99% |
| **Use date** | marcado, com intervalo dentro do período dos dados | evita rodar fora dos dados |
| **Period (timeframe)** | o que a estratégia usa (ex.: M15) | o tester gera a partir do M1 |
| **Spread** | **Current**/variável (com TDS) ou fixo realista | spread fixo otimista mente |
| **Visual mode** | desligado para rodar rápido; ligado só para depurar | velocidade |

Depois clique em **Start**.

### Conferindo a qualidade

1. Quando terminar, abra a aba **Report** (ou **Results**).
2. Procure **Modelling quality**. Tem que estar perto de **99.0% – 99.9%**.
   - Se aparecer **90%** → você **não** está usando tick data real. Volte: ou o
     símbolo está errado, ou você abriu o MT4 sem o patch do TDS, ou os
     `.fxt` não foram gerados.
   - Se aparecer **n/a / 25% / 0%** → faltam os dados M1/tick para o período.

---

## 5. Checklist final (imprima e siga)

- [ ] Tick data real instalado (Caminho A via Tickstory **ou** Caminho B via TDS).
- [ ] Nome do **Symbol** no tester é **idêntico** ao do broker/dados.
- [ ] **Model = Every tick**.
- [ ] Intervalo de **datas dentro** do período disponível (este repo:
      **2021-05-24 → 2026-05-24**).
- [ ] Spread variável (TDS) ou fixo realista — **nunca** o spread mínimo otimista.
- [ ] Offset de fuso/DST conferido se a estratégia depende de horário.
- [ ] Relatório mostrou **~99% Modelling Quality**. Se não, **não confie** e
      refaça.

---

## 6. Erros comuns e soluções rápidas

| Sintoma | Causa provável | Solução |
|---|---|---|
| Qualidade trava em **90%** | Sem tick data real / MT4 sem patch TDS | Use Tickstory (A) ou abra o MT4 pelo atalho do TDS (B) |
| "**mismatched charts errors**" no log | Buracos/ordem nos dados | Reexporte; com o script deste repo os ticks já vêm ordenados |
| Símbolo **não aparece** no tester | Nome diferente do broker | Use o nome **exato** do Market Watch ao exportar/importar |
| Resultado **bom demais** | Spread fixo otimista ou sem custos | Ative spread variável (TDS) e comissão/swap reais |
| Horário das entradas "deslocado" | Offset UTC vs. fuso do broker | Ajuste GMT offset + DST na exportação |
| Tester **lento** demais | Visual mode ligado / período enorme | Desligue Visual mode; teste por blocos (ex.: ano a ano) |

---

## 7. Resumo em uma frase para passar pro colega

> *"Instala o Tickstory (grátis), baixa o XAUUSD/US500, faz **Export to
> MetaTrader**, e no Strategy Tester do MT4 põe **Model = Every tick**. Confere no
> relatório se deu **99% de Modelling Quality** — se deu, o backtest vale; se deu
> 90%, refaz. Pra usar os dados deste repositório direto, roda o
> `tools/parquet_to_mt4_csv.py` e importa o CSV pelo Tick Data Suite."*

---

### Referências

- Tick Data Suite — https://eareview.net/tick-data-suite
- Tickstory: Backtest com 99% de qualidade — https://tickstory.com/articles/metatrader-back-test-with-99-modelling-quality/
- Tickstory: Exportar para o MetaTrader 4 — https://usermanual.tickstory.com/doku.php?id=video:exporting_to_metatrader_4
- Quick start do Tick Data Suite — https://support.eareview.net/support/solutions/articles/19000011254-quick-start-guide

> Conteúdo educacional. Não é recomendação de investimento.
