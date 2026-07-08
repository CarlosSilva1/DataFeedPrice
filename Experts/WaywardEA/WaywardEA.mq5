//+------------------------------------------------------------------+
//|                                                    WaywardEA.mq5  |
//|                              Mean-Reversion Scalping EA (MQL5)    |
//|                                                                  |
//| Strategy (as presented by "Mr. CapFree"):                        |
//|   - Bollinger Bands measure price stretch away from the mean     |
//|   - RSI confirms exhaustion (overbought / oversold)              |
//|   - A very long ATR (period 1000) gives extremely smoothed,      |
//|     slowly-moving distances used for candle-size filtering,      |
//|     stop-loss, trailing and pending-order placement.             |
//|                                                                  |
//| Entries use STOP orders placed beyond the current price so the   |
//| EA never "catches a falling knife": it waits for price to snap   |
//| back through the pending level before entering. The take-profit  |
//| is always the Bollinger middle line (the mean).                  |
//+------------------------------------------------------------------+
#property copyright "Wayward EA"
#property link      "https://github.com/CarlosSilva1/DataFeedPrice"
#property version   "1.00"
#property strict

//--- Standard MT5 trade library
#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\OrderInfo.mqh>

//--- Global instances
CTrade        trade;
CPositionInfo positionInfo;
COrderInfo    orderInfo;

//+------------------------------------------------------------------+
//| Enumerations                                                     |
//+------------------------------------------------------------------+
enum ENUM_HOUR
{
   H00=0, H01, H02, H03, H04, H05, H06, H07, H08, H09, H10, H11,
   H12, H13, H14, H15, H16, H17, H18, H19, H20, H21, H22, H23
};

enum ENUM_LOT_MODE
{
   LOT_FIXED=0,       // Fixed lot
   LOT_PCT_BALANCE,   // % of Balance
   LOT_PCT_EQUITY,    // % of Equity
   LOT_PCT_FREEMARGIN // % of Free Margin
};

//+------------------------------------------------------------------+
//| Inputs                                                           |
//+------------------------------------------------------------------+
//--- General
input group           "=== General ==="
input long            InpMagicNumber      = 20240707;      // Magic Number
input ENUM_TIMEFRAMES InpTimeframe        = PERIOD_CURRENT;// Working Timeframe
input ENUM_TIMEFRAMES InpHigherTimeframe  = PERIOD_H1;     // Higher TF (confluence)

//--- Session window
input group           "=== Trading Hours ==="
input ENUM_HOUR       InpStartHour        = H00;           // Start Hour
input ENUM_HOUR       InpEndHour          = H23;           // End Hour
input int             InpMaxOrderAgeBars  = 5;             // Max pending age (bars) 0=off

//--- Bollinger Bands
input group           "=== Bollinger Bands ==="
input int             InpBBPeriod         = 20;            // BB Period
input double          InpBBDeviation      = 2.0;           // BB Std Deviation
input ENUM_APPLIED_PRICE InpBBAppliedPrice= PRICE_CLOSE;   // BB Applied Price

//--- RSI
input group           "=== RSI ==="
input int             InpRSIPeriod        = 14;            // RSI Period
input ENUM_APPLIED_PRICE InpRSIAppliedPrice=PRICE_CLOSE;   // RSI Applied Price
input int             InpRSIFilter        = 30;            // RSI Filter (levels = 50-/+ ... => 20 / 80)

//--- ATR (long period for smoothing)
input group           "=== ATR ==="
input int             InpATRPeriod        = 1000;          // ATR Period (long / smoothed)

//--- Trade management (ATR multipliers)
input group           "=== Trade Management (ATR mult) ==="
input double          InpATRMultCandle    = 1.0;           // Candle size min (x ATR)
input double          InpSLATRMult        = 2.0;           // Stop-Loss (x ATR)
input double          InpTrailATRMult     = 0.2;           // Trailing (x ATR)
input double          InpOrderDistATRMult = 0.3;           // Pending order distance (x ATR)

//--- Execution filters
input group           "=== Execution Filters ==="
input int             InpMaxSpread        = 10;            // Max Spread (points)
input int             InpSlippage         = 10;            // Slippage (points)

//--- Money management
input group           "=== Money Management ==="
input ENUM_LOT_MODE   InpLotMode          = LOT_PCT_BALANCE;// Lot Mode
input double          InpFixedLot         = 0.01;          // Fixed lot (LOT_FIXED)
input double          InpRiskPercent      = 1.0;           // Risk % (percentage modes)

//+------------------------------------------------------------------+
//| Globals                                                          |
//+------------------------------------------------------------------+
int      hBands   = INVALID_HANDLE;
int      hRSI     = INVALID_HANDLE;
int      hATR     = INVALID_HANDLE;

double   g_point;
int      g_digits;
datetime g_lastBarTime = 0;

//--- Derived RSI levels from the filter (default 30 => 20 / 80)
double   g_rsiLower;   // oversold threshold
double   g_rsiUpper;   // overbought threshold

//+------------------------------------------------------------------+
//| Expert initialization                                            |
//+------------------------------------------------------------------+
int OnInit()
{
   //--- basic symbol info
   g_point  = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   g_digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);

   //--- configure trade object
   trade.SetExpertMagicNumber(InpMagicNumber);
   trade.SetDeviationInPoints(InpSlippage);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetMarginMode();
   trade.LogLevel(LOG_LEVEL_ERRORS);

   //--- cosmetic: remove chart grid
   ChartSetInteger(0, CHART_SHOW_GRID, false);

   //--- RSI levels: filter of 30 => 50-30 = 20 (oversold), 50+30 = 80 (overbought)
   g_rsiLower = 50.0 - (double)InpRSIFilter;
   g_rsiUpper = 50.0 + (double)InpRSIFilter;

   //--- indicator handles
   hBands = iBands(_Symbol, InpTimeframe, InpBBPeriod, 0, InpBBDeviation, InpBBAppliedPrice);
   hRSI   = iRSI (_Symbol, InpTimeframe, InpRSIPeriod, InpRSIAppliedPrice);
   hATR   = iATR (_Symbol, InpTimeframe, InpATRPeriod);

   if(hBands==INVALID_HANDLE || hRSI==INVALID_HANDLE || hATR==INVALID_HANDLE)
   {
      Print("Failed to create indicator handles.");
      return(INIT_FAILED);
   }

   //--- validate inputs
   if(InpStartHour==InpEndHour)
      Print("Warning: Start Hour equals End Hour -> trading window is a single hour.");

   Print("WaywardEA initialised. RSI levels: ", g_rsiLower, " / ", g_rsiUpper,
         "  ATR period: ", InpATRPeriod);

   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization                                          |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(hBands!=INVALID_HANDLE) IndicatorRelease(hBands);
   if(hRSI  !=INVALID_HANDLE) IndicatorRelease(hRSI);
   if(hATR  !=INVALID_HANDLE) IndicatorRelease(hATR);
}

//+------------------------------------------------------------------+
//| Expert tick                                                      |
//+------------------------------------------------------------------+
void OnTick()
{
   //--- read indicator values (index 0 = most recent / current forming bar)
   double bbUpper, bbLower, bbMiddle, rsi, atr;
   if(!getIndicatorValues(bbUpper, bbLower, bbMiddle, rsi, atr))
      return;

   if(atr<=0.0)
      return;

   //--- current prices
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);

   //--- current candle geometry
   double high = iHigh(_Symbol, InpTimeframe, 0);
   double low  = iLow (_Symbol, InpTimeframe, 0);
   double candleSize = high - low;

   //--- ATR-derived distances
   double candleThreshold = atr * InpATRMultCandle;
   double orderDistance   = atr * InpOrderDistATRMult;
   double slDistance      = atr * InpSLATRMult;

   //--- always manage what is already open first
   manageOpenPositions(atr);
   managePendingOrders(ask, bid, orderDistance);

   //--- housekeeping on pending order age (new bar only)
   if(isNewBar())
      close_all_orders();

   //--- entry logic: only when flat (no positions and no pending orders)
   if(hasOpenPositionOrOrder())
      return;

   //--- session filter
   if(!isTradingTime())
      return;

   //--- spread filter
   long spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   if(spread > InpMaxSpread)
      return;

   //--- signal conditions
   bool bigCandle = (candleSize > candleThreshold);

   bool buySignal  = bigCandle && (bid < bbLower) && (rsi < g_rsiLower);
   bool sellSignal = bigCandle && (ask > bbUpper) && (rsi > g_rsiUpper);

   if(buySignal)
      sendOrder(ORDER_TYPE_BUY_STOP, ask, bid, orderDistance, slDistance, bbMiddle);
   else if(sellSignal)
      sendOrder(ORDER_TYPE_SELL_STOP, ask, bid, orderDistance, slDistance, bbMiddle);
}

//+------------------------------------------------------------------+
//| Copy the latest indicator values (index 0)                       |
//+------------------------------------------------------------------+
bool getIndicatorValues(double &bbUpper, double &bbLower, double &bbMiddle,
                        double &rsi, double &atr)
{
   double up[1], lo[1], mid[1], r[1], a[1];

   if(CopyBuffer(hBands, 1, 0, 1, up)  < 1) return(false); // BASE_LINE=0, UPPER=1, LOWER=2
   if(CopyBuffer(hBands, 2, 0, 1, lo)  < 1) return(false);
   if(CopyBuffer(hBands, 0, 0, 1, mid) < 1) return(false);
   if(CopyBuffer(hRSI,   0, 0, 1, r)   < 1) return(false);
   if(CopyBuffer(hATR,   0, 0, 1, a)   < 1) return(false);

   bbUpper  = up[0];
   bbLower  = lo[0];
   bbMiddle = mid[0];
   rsi      = r[0];
   atr      = a[0];
   return(true);
}

//+------------------------------------------------------------------+
//| Place a pending STOP order with TP = Bollinger middle line       |
//+------------------------------------------------------------------+
void sendOrder(const ENUM_ORDER_TYPE type, const double ask, const double bid,
              const double orderDistance, const double slDistance,
              const double bbMiddle)
{
   double price, sl, tp;
   double stopLevel = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * g_point;

   if(type==ORDER_TYPE_BUY_STOP)
   {
      //--- entry above current Ask so we only buy on a snap-back up
      price = ask + orderDistance;
      //--- respect broker minimum stop distance
      if(price - ask < stopLevel) price = ask + stopLevel;

      sl = price - slDistance;
      tp = bbMiddle;                       // mean-reversion target

      //--- TP must sit above entry for a buy; skip if geometry is invalid
      if(tp <= price + stopLevel)
         return;
   }
   else // ORDER_TYPE_SELL_STOP
   {
      //--- entry below current Bid so we only sell on a snap-back down
      price = bid - orderDistance;
      if(bid - price < stopLevel) price = bid - stopLevel;

      sl = price + slDistance;
      tp = bbMiddle;

      if(tp >= price - stopLevel)
         return;
   }

   price = NormalizeDouble(price, g_digits);
   sl    = NormalizeDouble(sl,    g_digits);
   tp    = NormalizeDouble(tp,    g_digits);

   //--- lot from money management (risk over the SL distance)
   double lots = calcLots(slDistance);
   if(lots<=0.0)
      return;

   bool ok;
   if(type==ORDER_TYPE_BUY_STOP)
      ok = trade.BuyStop(lots, price, _Symbol, sl, tp, ORDER_TIME_GTC, 0, "WaywardEA");
   else
      ok = trade.SellStop(lots, price, _Symbol, sl, tp, ORDER_TIME_GTC, 0, "WaywardEA");

   if(!ok)
      Print("sendOrder failed: ", trade.ResultRetcode(), " - ", trade.ResultRetcodeDescription());
}

//+------------------------------------------------------------------+
//| Keep pending orders trailing the price at a constant ATR gap     |
//| If price keeps moving away (down for a buy-stop, up for a         |
//| sell-stop) the pending order is dragged along to preserve the    |
//| ATR distance, and its SL/TP mean target are re-derived.          |
//+------------------------------------------------------------------+
void managePendingOrders(const double ask, const double bid, const double orderDistance)
{
   double bbUpper, bbLower, bbMiddle, rsi, atr;
   if(!getIndicatorValues(bbUpper, bbLower, bbMiddle, rsi, atr))
      return;

   double slDistance = atr * InpSLATRMult;
   double stopLevel  = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * g_point;

   for(int i=OrdersTotal()-1; i>=0; i--)
   {
      if(!orderInfo.SelectByIndex(i))
         continue;
      if(orderInfo.Symbol()!=_Symbol || orderInfo.Magic()!=InpMagicNumber)
         continue;

      ENUM_ORDER_TYPE type = orderInfo.OrderType();

      if(type==ORDER_TYPE_BUY_STOP)
      {
         double desired = ask + orderDistance;
         if(desired - ask < stopLevel) desired = ask + stopLevel;
         desired = NormalizeDouble(desired, g_digits);

         //--- only pull the order DOWN toward price (price fell away): keep the gap tight
         if(desired < orderInfo.PriceOpen() - g_point)
         {
            double sl = NormalizeDouble(desired - slDistance, g_digits);
            double tp = NormalizeDouble(bbMiddle, g_digits);
            if(tp > desired + stopLevel)
               trade.OrderModify(orderInfo.Ticket(), desired, sl, tp, ORDER_TIME_GTC, 0);
         }
      }
      else if(type==ORDER_TYPE_SELL_STOP)
      {
         double desired = bid - orderDistance;
         if(bid - desired < stopLevel) desired = bid - stopLevel;
         desired = NormalizeDouble(desired, g_digits);

         //--- only push the order UP toward price (price rose away)
         if(desired > orderInfo.PriceOpen() + g_point)
         {
            double sl = NormalizeDouble(desired + slDistance, g_digits);
            double tp = NormalizeDouble(bbMiddle, g_digits);
            if(tp < desired - stopLevel)
               trade.OrderModify(orderInfo.Ticket(), desired, sl, tp, ORDER_TIME_GTC, 0);
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Trailing stop on open positions at ATR * TrailMult               |
//+------------------------------------------------------------------+
void manageOpenPositions(const double atr)
{
   double trailDistance = atr * InpTrailATRMult;
   double stopLevel     = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * g_point;

   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);

   for(int i=PositionsTotal()-1; i>=0; i--)
   {
      if(!positionInfo.SelectByIndex(i))
         continue;
      if(positionInfo.Symbol()!=_Symbol || positionInfo.Magic()!=InpMagicNumber)
         continue;

      double openPrice = positionInfo.PriceOpen();
      double curSL     = positionInfo.StopLoss();
      double curTP     = positionInfo.TakeProfit();

      if(positionInfo.PositionType()==POSITION_TYPE_BUY)
      {
         //--- only trail once in profit
         if(bid <= openPrice)
            continue;

         double newSL = NormalizeDouble(bid - trailDistance, g_digits);

         //--- respect broker min distance and never move SL backwards
         if(bid - newSL < stopLevel)
            newSL = NormalizeDouble(bid - stopLevel, g_digits);

         if(newSL > openPrice && (curSL==0.0 || newSL > curSL + g_point))
            trade.PositionModify(positionInfo.Ticket(), newSL, curTP);
      }
      else // POSITION_TYPE_SELL
      {
         if(ask >= openPrice)
            continue;

         double newSL = NormalizeDouble(ask + trailDistance, g_digits);

         if(newSL - ask < stopLevel)
            newSL = NormalizeDouble(ask + stopLevel, g_digits);

         if(newSL < openPrice && (curSL==0.0 || newSL < curSL - g_point))
            trade.PositionModify(positionInfo.Ticket(), newSL, curTP);
      }
   }
}

//+------------------------------------------------------------------+
//| Money management: lot from risk over the SL distance             |
//+------------------------------------------------------------------+
double calcLots(const double slDistance)
{
   //--- fixed lot mode
   if(InpLotMode==LOT_FIXED)
      return(normalizeLot(InpFixedLot));

   //--- risk capital base
   double base = 0.0;
   switch(InpLotMode)
   {
      case LOT_PCT_BALANCE:    base = AccountInfoDouble(ACCOUNT_BALANCE);     break;
      case LOT_PCT_EQUITY:     base = AccountInfoDouble(ACCOUNT_EQUITY);      break;
      case LOT_PCT_FREEMARGIN: base = AccountInfoDouble(ACCOUNT_MARGIN_FREE); break;
      default:                 base = AccountInfoDouble(ACCOUNT_BALANCE);     break;
   }

   double riskMoney = base * (InpRiskPercent/100.0);
   if(riskMoney<=0.0 || slDistance<=0.0)
      return(0.0);

   //--- value of a 1.0-lot move over the SL distance
   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickValue<=0.0 || tickSize<=0.0)
      return(0.0);

   //--- loss (per 1 lot) if the SL distance is hit
   double lossPerLot = (slDistance / tickSize) * tickValue;
   if(lossPerLot<=0.0)
      return(0.0);

   double lots = riskMoney / lossPerLot;
   return(normalizeLot(lots));
}

//+------------------------------------------------------------------+
//| Clamp a lot to broker MinLot / MaxLot / LotStep                  |
//+------------------------------------------------------------------+
double normalizeLot(double lots)
{
   double minLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

   if(lotStep<=0.0) lotStep = 0.01;

   //--- round down to the nearest step
   lots = MathFloor(lots/lotStep) * lotStep;

   if(lots < minLot) lots = minLot;
   if(lots > maxLot) lots = maxLot;

   //--- normalise decimals to the step
   int lotDigits = (int)MathRound(-MathLog10(lotStep));
   if(lotDigits < 0) lotDigits = 0;
   lots = NormalizeDouble(lots, lotDigits);

   return(lots);
}

//+------------------------------------------------------------------+
//| Is there anything of ours open (position or pending order)?      |
//+------------------------------------------------------------------+
bool hasOpenPositionOrOrder()
{
   for(int i=PositionsTotal()-1; i>=0; i--)
   {
      if(positionInfo.SelectByIndex(i) &&
         positionInfo.Symbol()==_Symbol && positionInfo.Magic()==InpMagicNumber)
         return(true);
   }
   for(int i=OrdersTotal()-1; i>=0; i--)
   {
      if(orderInfo.SelectByIndex(i) &&
         orderInfo.Symbol()==_Symbol && orderInfo.Magic()==InpMagicNumber)
         return(true);
   }
   return(false);
}

//+------------------------------------------------------------------+
//| New bar detector                                                 |
//+------------------------------------------------------------------+
bool isNewBar()
{
   datetime t = iTime(_Symbol, InpTimeframe, 0);
   if(t!=g_lastBarTime)
   {
      g_lastBarTime = t;
      return(true);
   }
   return(false);
}

//+------------------------------------------------------------------+
//| Session window filter. Deletes pendings while outside window.    |
//+------------------------------------------------------------------+
bool isTradingTime()
{
   MqlDateTime dt;
   TimeCurrent(dt);
   int hour = dt.hour;

   bool inWindow;
   if(InpStartHour <= InpEndHour)
      inWindow = (hour >= InpStartHour && hour <= InpEndHour);
   else
      //--- window wraps past midnight
      inWindow = (hour >= InpStartHour || hour <= InpEndHour);

   if(!inWindow)
   {
      //--- outside the window: cancel any resting pendings
      deleteAllPendings();
      return(false);
   }
   return(true);
}

//+------------------------------------------------------------------+
//| Delete pending orders whose age exceeded InpMaxOrderAgeBars      |
//+------------------------------------------------------------------+
void close_all_orders()
{
   if(InpMaxOrderAgeBars<=0)
      return;

   int    barSeconds = PeriodSeconds(InpTimeframe);
   datetime now      = TimeCurrent();

   for(int i=OrdersTotal()-1; i>=0; i--)
   {
      if(!orderInfo.SelectByIndex(i))
         continue;
      if(orderInfo.Symbol()!=_Symbol || orderInfo.Magic()!=InpMagicNumber)
         continue;

      long ageSeconds = (long)(now - orderInfo.TimeSetup());
      if(ageSeconds >= (long)InpMaxOrderAgeBars * barSeconds)
         trade.OrderDelete(orderInfo.Ticket());
   }
}

//+------------------------------------------------------------------+
//| Delete every pending order belonging to this EA                  |
//+------------------------------------------------------------------+
void deleteAllPendings()
{
   for(int i=OrdersTotal()-1; i>=0; i--)
   {
      if(!orderInfo.SelectByIndex(i))
         continue;
      if(orderInfo.Symbol()!=_Symbol || orderInfo.Magic()!=InpMagicNumber)
         continue;
      trade.OrderDelete(orderInfo.Ticket());
   }
}
//+------------------------------------------------------------------+
