//+------------------------------------------------------------------+
//| EngineStrategy.mq5                                               |
//| The engine's portfolio strategies as a plain MT5 EA, to validate |
//| the engine against the MT5 Strategy Tester.                      |
//|                                                                  |
//| Same rules as engine/strategies.py + engine/backtest.py:         |
//|  - decides once per new bar, using the bar that just CLOSED,     |
//|  - long only, one position, market order on the new bar,         |
//|  - lots = floor(Exposure * equity / (ask * contract) / step),    |
//|    fixed for the life of the trade.                              |
//|                                                                  |
//| Strategies (pick with the Strategy input):                       |
//|  RSI_REVERSION : buy when RSI(RsiPeriod) < RsiBuyBelow,          |
//|                  close when RSI > RsiExitAbove                   |
//|  MA_CROSS      : long while EMA(FastEMA) > EMA(SlowEMA)          |
//|  TREND_EMA     : long while Close > EMA(TrendEMA)                |
//|                                                                  |
//| Tester settings to match the engine: see mt5/VALIDATION.md.      |
//| NOT compiled or tested in this repo.                             |
//+------------------------------------------------------------------+
#property strict
#include <Trade/Trade.mqh>

enum ENUM_ENGINE_STRATEGY { RSI_REVERSION = 0, MA_CROSS = 1, TREND_EMA = 2 };

input ENUM_ENGINE_STRATEGY Strategy = RSI_REVERSION;
input double Exposure      = 1.0;    // position notional as a multiple of equity (engine "leverage")
input int    RsiPeriod     = 2;      // RSI_REVERSION
input double RsiBuyBelow   = 10.0;
input double RsiExitAbove  = 50.0;
input int    FastEMA       = 10;     // MA_CROSS
input int    SlowEMA       = 50;
input int    TrendEMA      = 50;     // TREND_EMA
input long   Magic         = 8811001;
input int    MaxDeviationPts = 50;

CTrade   trade;
int      hRsi = INVALID_HANDLE, hFast = INVALID_HANDLE, hSlow = INVALID_HANDLE, hTrend = INVALID_HANDLE;
datetime lastBar = 0;

int OnInit()
{
   trade.SetExpertMagicNumber(Magic);
   trade.SetDeviationInPoints((ulong)MaxDeviationPts);
   trade.SetTypeFillingBySymbol(_Symbol);
   if(Strategy == RSI_REVERSION) hRsi = iRSI(_Symbol, _Period, RsiPeriod, PRICE_CLOSE);
   if(Strategy == MA_CROSS)
   {
      hFast = iMA(_Symbol, _Period, FastEMA, 0, MODE_EMA, PRICE_CLOSE);
      hSlow = iMA(_Symbol, _Period, SlowEMA, 0, MODE_EMA, PRICE_CLOSE);
   }
   if(Strategy == TREND_EMA) hTrend = iMA(_Symbol, _Period, TrendEMA, 0, MODE_EMA, PRICE_CLOSE);
   if((Strategy == RSI_REVERSION && hRsi == INVALID_HANDLE) ||
      (Strategy == MA_CROSS && (hFast == INVALID_HANDLE || hSlow == INVALID_HANDLE)) ||
      (Strategy == TREND_EMA && hTrend == INVALID_HANDLE))
   {
      Print("Indicator handle failed");
      return INIT_FAILED;
   }
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(hRsi   != INVALID_HANDLE) IndicatorRelease(hRsi);
   if(hFast  != INVALID_HANDLE) IndicatorRelease(hFast);
   if(hSlow  != INVALID_HANDLE) IndicatorRelease(hSlow);
   if(hTrend != INVALID_HANDLE) IndicatorRelease(hTrend);
}

// Value of an indicator on the last CLOSED bar (shift 1).
bool Closed(const int handle, double &v)
{
   double b[1];
   if(CopyBuffer(handle, 0, 1, 1, b) != 1) return false;
   v = b[0];
   return true;
}

ulong MyTicket()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(PositionSelectByTicket(t) && PositionGetString(POSITION_SYMBOL) == _Symbol &&
         PositionGetInteger(POSITION_MAGIC) == Magic) return t;
   }
   return 0;
}

void OpenLong()
{
   double eq   = AccountInfoDouble(ACCOUNT_EQUITY);
   double ask  = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double cs   = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_CONTRACT_SIZE);
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double vmax = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   if(ask <= 0 || cs <= 0 || step <= 0) return;
   double lots = MathFloor(Exposure * eq / (ask * cs) / step + 1e-9) * step;
   if(lots > vmax) lots = vmax;
   lots = NormalizeDouble(lots, 8);
   if(lots < vmin) { PrintFormat("Lot %.4f below minimum %.4f, entry skipped", lots, vmin); return; }
   if(!trade.Buy(lots, _Symbol)) Print("Buy failed: ", trade.ResultRetcodeDescription());
}

void OnTick()
{
   datetime t = iTime(_Symbol, _Period, 0);
   if(t == lastBar) return;                       // act once per new bar

   bool entry = false, exit = false;
   if(Strategy == RSI_REVERSION)
   {
      double r;
      if(!Closed(hRsi, r)) return;
      entry = (r < RsiBuyBelow);
      exit  = (r > RsiExitAbove);
   }
   else if(Strategy == MA_CROSS)
   {
      double f, s;
      if(!Closed(hFast, f) || !Closed(hSlow, s)) return;
      entry = (f > s);
      exit  = !entry;
   }
   else
   {
      double e;
      if(!Closed(hTrend, e)) return;
      entry = (iClose(_Symbol, _Period, 1) > e);
      exit  = !entry;
   }
   lastBar = t;

   ulong ticket = MyTicket();
   if(ticket != 0 && exit)
   {
      if(!trade.PositionClose(ticket)) { Print("Close failed: ", trade.ResultRetcodeDescription()); lastBar = 0; }
      return;
   }
   if(ticket == 0 && entry) OpenLong();
}
