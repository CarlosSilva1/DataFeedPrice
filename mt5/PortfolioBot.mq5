//+------------------------------------------------------------------+
//| PortfolioBot.mq5                                                 |
//| One EA trades the whole engine portfolio on one MT5 account.     |
//|                                                                  |
//| Every TimerSeconds it reads engine/output/orders_latest.json     |
//| (from a URL via WebRequest, e.g. the GitHub raw URL, or from the |
//| Common Files folder) and reconciles ONE POSITION PER COMBO       |
//| (magic = Magic + magic_offset) with the engine's signal:         |
//|   signal 0 or opposite  -> close the combo's position            |
//|   signal on, no position-> open                                  |
//|        lots = floor(exposure% * equity / (price*contract) / step)|
//|   signal on, position on-> hold (lot size is fixed at entry)     |
//| This is exactly what engine/portfolio.py simulate_account tests. |
//| If the market is closed the order fails and is retried on the    |
//| next timer.                                                      |
//|                                                                  |
//| Needs a HEDGING account. Setup: Tools > Options > Expert Advisors|
//| > Allow WebRequest for https://raw.githubusercontent.com .       |
//| Attach to any one chart.                                         |
//| NOT compiled or tested in this repo: run on a demo account first.|
//+------------------------------------------------------------------+
#property strict
#include <Trade/Trade.mqh>

input string OrdersURL        = "https://raw.githubusercontent.com/CarlosSilva1/DataFeedPrice/claude/sleepy-hypatia-xi4g3r/engine/output/orders_latest.json";
input string OrdersFile       = "orders_latest.json"; // used when OrdersURL is empty (Common Files folder)
input string BotId            = "SET_ME";             // must equal bot_id in engine/config/bot.json
input long   Magic            = 8800000;              // combos use Magic+1 .. Magic+90000
input int    TimerSeconds     = 30;
input int    MaxDeviationPts  = 50;                   // max slippage accepted per order
input double MaxOrderAgeHours = 12;                   // ignore an orders file older than this (holds positions)
input bool   DryRun           = true;                 // log only; set false to trade

CTrade trade;

int OnInit()
{
   if((ENUM_ACCOUNT_MARGIN_MODE)AccountInfoInteger(ACCOUNT_MARGIN_MODE) != ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)
   {
      Print("STOP: PortfolioBot needs a hedging account (one position per combo).");
      return INIT_FAILED;
   }
   trade.SetDeviationInPoints((ulong)MaxDeviationPts);
   EventSetTimer(TimerSeconds);
   Print("PortfolioBot ", BotId, " started. DryRun=", DryRun);
   return INIT_SUCCEEDED;
}
void OnDeinit(const int reason) { EventKillTimer(); }

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
   string s = "";
   while(!FileIsEnding(h)) s += FileReadString(h) + "\n";
   FileClose(h);
   return s;
}

// Minimal JSON readers for the engine's fixed format. pos = -1 when the key is not found.
string JStr(const string js, const string key, const int from, int &pos)
{
   int k = StringFind(js, "\"" + key + "\"", from);
   if(k < 0) { pos = -1; return ""; }
   int c  = StringFind(js, ":", k);
   int q1 = StringFind(js, "\"", c + 1);
   int q2 = StringFind(js, "\"", q1 + 1);
   pos = q2;
   return StringSubstr(js, q1 + 1, q2 - q1 - 1);
}
double JNum(const string js, const string key, const int from, int &pos)
{
   int k = StringFind(js, "\"" + key + "\"", from);
   if(k < 0) { pos = -1; return 0; }
   int c = StringFind(js, ":", k);
   int e = c + 1;
   while(e < StringLen(js))
   {
      string ch = StringSubstr(js, e, 1);
      if(ch == "," || ch == "}" || ch == "\n" || ch == "]") break;
      e++;
   }
   pos = e;
   return StringToDouble(StringSubstr(js, c + 1, e - c - 1));
}
bool JTrue(const string js, const string key)
{
   int k = StringFind(js, "\"" + key + "\"");
   if(k < 0) return true;                       // missing flag = treat as stale
   int c = StringFind(js, ":", k);
   return StringFind(StringSubstr(js, c + 1, 8), "true") >= 0;
}

ulong FindPosition(const string sym, const long magic)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(!PositionSelectByTicket(t)) continue;
      if(PositionGetString(POSITION_SYMBOL) == sym && PositionGetInteger(POSITION_MAGIC) == magic) return t;
   }
   return 0;
}

void Reconcile(const string combo, const string sym, const long magic, const double expoPct)
{
   int want = (expoPct > 0) ? 1 : ((expoPct < 0) ? -1 : 0);
   ulong ticket = FindPosition(sym, magic);
   if(ticket != 0 && PositionSelectByTicket(ticket))
   {
      int have = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? 1 : -1;
      if(have == want) return;                                   // hold: size is fixed at entry
      PrintFormat("%s: close %s (signal %d)", combo, sym, want);
      if(DryRun) return;
      trade.SetExpertMagicNumber(magic);
      if(!trade.PositionClose(ticket)) { Print(combo, ": close failed, will retry: ", trade.ResultRetcodeDescription()); return; }
   }
   if(want == 0) return;
   if(!SymbolSelect(sym, true)) { Print("STOP: symbol ", sym, " is not available on this account"); return; }
   double eq   = AccountInfoDouble(ACCOUNT_EQUITY);
   double px   = (want > 0) ? SymbolInfoDouble(sym, SYMBOL_ASK) : SymbolInfoDouble(sym, SYMBOL_BID);
   double cs   = SymbolInfoDouble(sym, SYMBOL_TRADE_CONTRACT_SIZE);
   double step = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP);
   double vmin = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
   double vmax = SymbolInfoDouble(sym, SYMBOL_VOLUME_MAX);
   if(px <= 0 || cs <= 0 || step <= 0) { Print("No price/spec for ", sym); return; }
   double lots = MathFloor(MathAbs(expoPct) / 100.0 * eq / (px * cs) / step + 1e-9) * step;
   if(lots > vmax) lots = vmax;
   lots = NormalizeDouble(lots, 8);
   if(lots < vmin) { PrintFormat("%s: lot %.4f below minimum %.4f for %s, skipped", combo, lots, vmin, sym); return; }
   PrintFormat("%s: open %s %s %.2f lots (%.2f%% of NAV)", combo, (want > 0 ? "BUY" : "SELL"), sym, lots, expoPct);
   if(DryRun) return;
   trade.SetExpertMagicNumber(magic);
   trade.SetTypeFillingBySymbol(sym);
   bool ok = (want > 0) ? trade.Buy(lots, sym, 0, 0, 0, StringSubstr(combo, 0, 31))
                        : trade.Sell(lots, sym, 0, 0, 0, StringSubstr(combo, 0, 31));
   if(!ok) Print(combo, ": order failed, will retry: ", trade.ResultRetcodeDescription());
}

void OnTimer()
{
   string js = LoadOrders();
   if(js == "") return;
   int p;
   string bot = JStr(js, "bot_id", 0, p);
   if(bot != BotId) { Print("STOP: orders are for bot ", bot, ", this EA is ", BotId); return; }
   if(JTrue(js, "stale")) { Print("STOP: engine says price data is stale; holding positions"); return; }
   datetime gen = StringToTime(JStr(js, "generated_at_mt5", 0, p));
   if(TimeGMT() - gen > (long)(MaxOrderAgeHours * 3600)) { Print("Orders file is too old; holding positions"); return; }

   int from = StringFind(js, "\"combos\"");
   int end  = StringFind(js, "\"net_by_pair\"");
   if(from < 0) { Print("No combos in orders file"); return; }
   if(end < 0) end = StringLen(js);
   long seen[]; int n = 0;
   while(true)
   {
      string combo = JStr(js, "combo", from, p);
      if(p < 0 || p > end) break;
      string pair = JStr(js, "pair", p, p);                    if(p < 0) break;
      long   off  = (long)JNum(js, "magic_offset", p, p);      if(p < 0) break;
      double expo = JNum(js, "exposure_pct_nav", p, p);        if(p < 0) break;
      from = p;
      ArrayResize(seen, n + 1); seen[n++] = Magic + off;
      Reconcile(combo, pair, Magic + off, expo);
   }
   // Close positions of combos that left the portfolio.
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(!PositionSelectByTicket(t)) continue;
      long m = PositionGetInteger(POSITION_MAGIC);
      if(m <= Magic || m > Magic + 90000) continue;
      bool keep = false;
      for(int k = 0; k < n; k++) if(seen[k] == m) { keep = true; break; }
      if(keep) continue;
      Print("Closing position of a combo no longer in the portfolio, magic ", m);
      if(!DryRun) { trade.SetExpertMagicNumber(m); trade.PositionClose(t); }
   }
}
