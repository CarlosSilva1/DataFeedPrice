//+------------------------------------------------------------------+
//| PortfolioBot.mq5                                                 |
//| One EA trades the whole engine portfolio on one MT5 account.     |
//|                                                                  |
//| Every TimerSeconds it reads engine/output/orders_latest.json     |
//| (from a URL via WebRequest, e.g. the GitHub raw URL, or from     |
//| MQL5/Files/Common), checks bot_id and staleness, and moves each  |
//| pair's net position (this EA's magic only) to                    |
//|   lots = target_exposure_pct_nav/100 * equity / (price*contract) |
//|                                                                  |
//| Setup: Tools > Options > Expert Advisors > Allow WebRequest for  |
//| https://raw.githubusercontent.com . Attach to any one chart.     |
//| NOT compiled or tested in this repo: run on a demo account first.|
//+------------------------------------------------------------------+
#property strict
#include <Trade/Trade.mqh>

input string OrdersURL     = "https://raw.githubusercontent.com/CarlosSilva1/DataFeedPrice/claude/sleepy-hypatia-xi4g3r/engine/output/orders_latest.json";
input string OrdersFile    = "orders_latest.json";   // used when OrdersURL is empty (Common Files folder)
input string BotId         = "SET_ME";               // must equal bot_id in engine/config/bot.json
input long   Magic         = 880001;
input int    TimerSeconds  = 60;
input double MaxDeviationPts = 50;                   // max slippage accepted per order
input double RebalanceBandPct = 2.0;                 // skip changes smaller than this % of NAV
input bool   DryRun        = true;                   // log only; set false to trade

CTrade trade;
string lastGenerated = "";

int OnInit()
{
   trade.SetExpertMagicNumber(Magic);
   trade.SetDeviationInPoints((ulong)MaxDeviationPts);
   EventSetTimer(TimerSeconds);
   Print("PortfolioBot ", BotId, " started. DryRun=", DryRun);
   return INIT_SUCCEEDED;
}
void OnDeinit(const int r) { EventKillTimer(); }

string LoadOrders()
{
   if(StringLen(OrdersURL) > 0)
   {
      char data[], result[]; string headers;
      int code = WebRequest("GET", OrdersURL, "", 10000, data, result, headers);
      if(code != 200) { Print("WebRequest failed: ", code, " err ", GetLastError()); return ""; }
      return CharArrayToString(result, 0, WHOLE_ARRAY, CP_UTF8);
   }
   int h = FileOpen(OrdersFile, FILE_READ|FILE_TXT|FILE_COMMON|FILE_ANSI);
   if(h == INVALID_HANDLE) { Print("Cannot open ", OrdersFile); return ""; }
   string s = ""; while(!FileIsEnding(h)) s += FileReadString(h) + "\n";
   FileClose(h); return s;
}

// Minimal JSON helpers for the engine's fixed format.
string JStr(const string js, const string key, int from, int &pos)
{
   int k = StringFind(js, "\"" + key + "\"", from); if(k < 0) { pos = -1; return ""; }
   int c = StringFind(js, ":", k); int q1 = StringFind(js, "\"", c + 1); int q2 = StringFind(js, "\"", q1 + 1);
   pos = q2; return StringSubstr(js, q1 + 1, q2 - q1 - 1);
}
double JNum(const string js, const string key, int from, int &pos)
{
   int k = StringFind(js, "\"" + key + "\"", from); if(k < 0) { pos = -1; return 0; }
   int c = StringFind(js, ":", k); int e = c + 1;
   while(e < StringLen(js) && StringFind(",}\n]", StringSubstr(js, e, 1)) < 0) e++;
   pos = e; return StringToDouble(StringSubstr(js, c + 1, e - c - 1));
}
bool JBool(const string js, const string key)
{
   int k = StringFind(js, "\"" + key + "\""); if(k < 0) return true;
   int c = StringFind(js, ":", k); return StringFind(StringSubstr(js, c + 1, 8), "true") >= 0;
}

double NetLots(const string sym)
{
   double net = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(!PositionSelectByTicket(t)) continue;
      if(PositionGetString(POSITION_SYMBOL) != sym || PositionGetInteger(POSITION_MAGIC) != Magic) continue;
      double v = PositionGetDouble(POSITION_VOLUME);
      net += (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? v : -v;
   }
   return net;
}

void CloseAll(const string sym)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(PositionSelectByTicket(t) && PositionGetString(POSITION_SYMBOL) == sym && PositionGetInteger(POSITION_MAGIC) == Magic)
         trade.PositionClose(t);
   }
}

void Rebalance(const string sym, double expoPct)
{
   if(!SymbolSelect(sym, true)) { Print("STOP: symbol ", sym, " not available on this account"); return; }
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   double px = SymbolInfoDouble(sym, SYMBOL_BID);
   double cs = SymbolInfoDouble(sym, SYMBOL_TRADE_CONTRACT_SIZE);
   double step = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP), vmin = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
   if(px <= 0 || cs <= 0 || step <= 0) { Print("No price/spec for ", sym); return; }
   double target = MathRound(expoPct / 100.0 * eq / (px * cs) / step) * step;
   if(MathAbs(target) < vmin) target = 0;
   double cur = NetLots(sym);
   double diffPct = MathAbs(target - cur) * px * cs / eq * 100.0;
   PrintFormat("%s target %.2f%% NAV -> %.2f lots (now %.2f)", sym, expoPct, target, cur);
   if(diffPct < RebalanceBandPct && !(target == 0 && cur != 0)) return;
   if(DryRun) return;
   if(target == 0 || (cur != 0 && MathSignum(target) != MathSignum(cur))) { CloseAll(sym); cur = 0; }
   double d = NormalizeDouble(target - cur, 8);
   if(d > 0) trade.Buy(d, sym);
   else if(d < 0)
   {  // reduce longs / add shorts
      if(cur > 0) { // partial close of longs
         for(int i = PositionsTotal() - 1; i >= 0 && d < 0; i--)
         {
            ulong t = PositionGetTicket(i);
            if(!PositionSelectByTicket(t) || PositionGetString(POSITION_SYMBOL) != sym || PositionGetInteger(POSITION_MAGIC) != Magic) continue;
            double v = MathMin(PositionGetDouble(POSITION_VOLUME), -d);
            if(trade.PositionClosePartial(t, v)) d += v;
         }
      }
      else trade.Sell(-d, sym);
   }
}

void OnTimer()
{
   string js = LoadOrders(); if(js == "") return;
   int p;
   string bot = JStr(js, "bot_id", 0, p);
   if(bot != BotId) { Print("STOP: orders are for bot ", bot, ", this EA is ", BotId); return; }
   if(JBool(js, "stale")) { Print("STOP: engine says price data is stale; not trading"); return; }
   string gen = JStr(js, "generated_at", 0, p);
   if(gen == lastGenerated) return;
   int from = StringFind(js, "\"targets\"");
   while(true)
   {
      string pair = JStr(js, "pair", from, p); if(p < 0) break;
      double expo = JNum(js, "target_exposure_pct_nav", p, p); if(p < 0) break;
      Rebalance(pair, expo);
      from = p;
   }
   lastGenerated = gen;
}
