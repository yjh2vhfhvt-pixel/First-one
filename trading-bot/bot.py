"""Krypto Paper Trading Bot: RSI Mean Reversion mit Trendfilter und Stop Loss.

Handelt NUR mit Spielgeld. Kursdaten kommen live und kostenlos von der Boerse (ohne API Key).

  python bot.py backtest            Strategie auf historischen Daten testen
  python bot.py paper               Live mit Spielgeld handeln (laeuft dauerhaft)
  python bot.py backtest --csv d.csv  Backtest mit eigener CSV (timestamp,open,high,low,close,volume)
"""
import argparse, json, os, sys, time
from datetime import datetime, timezone

import pandas as pd

# ---------- Einstellungen ----------
EXCHANGE = "binance"          # oeffentliche Kursdaten, kein Konto noetig
SYMBOL = "BTC/USDT"
TIMEFRAME = "1h"
START_CAPITAL = 1000.0        # Spielgeld in USDT
RISK_FRACTION = 0.25          # Anteil vom Kapital pro Trade
FEE = 0.001                   # 0.1 % Gebuehr pro Kauf/Verkauf
RSI_LEN = 14
RSI_BUY = 30                  # kaufen wenn RSI darunter (ueberverkauft)
RSI_SELL = 55                 # verkaufen wenn RSI darueber (erholt)
TREND_LEN = 200               # nur kaufen wenn Kurs ueber SMA200 (kein Kauf im Absturz)
STOP_LOSS = 0.04              # 4 % Verlust -> raus
MAX_HOLD = 72                 # spaetestens nach 72 Kerzen verkaufen
STATE_FILE = "paper_state.json"
LOG_FILE = "trades.csv"
# -----------------------------------


def indicators(df):
    d = df["close"].diff()
    gain = d.clip(lower=0).ewm(alpha=1 / RSI_LEN, adjust=False).mean()
    loss = (-d.clip(upper=0)).ewm(alpha=1 / RSI_LEN, adjust=False).mean()
    df["rsi"] = 100 - 100 / (1 + gain / loss.replace(0, 1e-12))
    df["sma"] = df["close"].rolling(TREND_LEN).mean()
    return df


def signal(row, in_pos, bars_held):
    """Entscheidung auf Basis einer abgeschlossenen Kerze."""
    if pd.isna(row["sma"]):
        return "hold"
    if not in_pos and row["rsi"] < RSI_BUY and row["close"] > row["sma"]:
        return "buy"
    if in_pos and (row["rsi"] > RSI_SELL or bars_held >= MAX_HOLD):
        return "sell"
    return "hold"


def fetch(limit_bars):
    import ccxt
    ex = getattr(ccxt, EXCHANGE)({"enableRateLimit": True})
    ms = ex.parse_timeframe(TIMEFRAME) * 1000
    since = ex.milliseconds() - limit_bars * ms
    rows = []
    while since < ex.milliseconds():
        batch = ex.fetch_ohlcv(SYMBOL, TIMEFRAME, since=since, limit=1000)
        if not batch:
            break
        rows += batch
        since = batch[-1][0] + ms
    df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    return df.drop_duplicates("timestamp").reset_index(drop=True)


class Account:
    def __init__(self, cash=START_CAPITAL):
        self.cash, self.qty, self.entry, self.held, self.trades = cash, 0.0, 0.0, 0, []

    def buy(self, price, ts):
        spend = self.cash * RISK_FRACTION
        self.qty = spend * (1 - FEE) / price
        self.cash -= spend
        self.entry, self.held = price, 0
        log(ts, "KAUF", price, self.qty, self.cash)

    def sell(self, price, ts, reason):
        gross = self.qty * price * (1 - FEE)
        cost = self.qty * self.entry / (1 - FEE)
        self.cash += gross
        self.trades.append(gross / cost - 1)
        log(ts, f"VERKAUF ({reason})", price, self.qty, self.cash)
        self.qty = 0.0

    def value(self, price):
        return self.cash + self.qty * price


QUIET = False


def log(ts, action, price, qty, cash):
    t = datetime.fromtimestamp(ts / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M")
    if not QUIET:
        print(f"{t}  {action:<22} Preis {price:>10.2f}  Menge {qty:.6f}  Cash {cash:.2f}")
    new = not os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a") as f:
        if new:
            f.write("zeit,aktion,preis,menge,cash\n")
        f.write(f"{t},{action},{price:.2f},{qty:.8f},{cash:.2f}\n")


def backtest(df):
    """Signal auf Kerze i, Ausfuehrung zum Eroeffnungskurs von Kerze i+1 (kein Blick in die Zukunft)."""
    df = indicators(df)
    acc, peak, max_dd, pending = Account(), START_CAPITAL, 0.0, "hold"
    for i in range(len(df)):
        r = df.iloc[i]
        if pending == "buy":
            acc.buy(r["open"], r["timestamp"])
        elif pending == "sell" and acc.qty:
            acc.sell(r["open"], r["timestamp"], "Signal")
        pending = "hold"
        if acc.qty:
            stop = acc.entry * (1 - STOP_LOSS)
            if r["low"] <= stop:
                acc.sell(min(stop, r["open"]), r["timestamp"], "Stop Loss")
            else:
                acc.held += 1
        pending = signal(r, acc.qty > 0, acc.held)
        v = acc.value(r["close"])
        peak = max(peak, v)
        max_dd = max(max_dd, 1 - v / peak)
    end = acc.value(df["close"].iloc[-1])
    wins = [t for t in acc.trades if t > 0]
    hodl = df["close"].iloc[-1] / df["close"].iloc[0] - 1
    print("\n===== Backtest =====")
    print(f"Zeitraum:        {len(df)} Kerzen ({TIMEFRAME})")
    print(f"Endkapital:      {end:.2f} USDT ({end / START_CAPITAL - 1:+.2%})")
    print(f"Nur halten:      {hodl:+.2%} (zum Vergleich)")
    print(f"Trades:          {len(acc.trades)}, Trefferquote {len(wins) / max(len(acc.trades), 1):.0%}")
    print(f"Max. Drawdown:   {max_dd:.2%}")
    return end


def paper():
    import ccxt
    ex = getattr(ccxt, EXCHANGE)({"enableRateLimit": True})
    acc = Account()
    last_ts = None
    if os.path.exists(STATE_FILE):
        acc.__dict__.update(json.load(open(STATE_FILE)))
        last_ts = acc.__dict__.pop("last_ts", None)
    print(f"Paper Trading {SYMBOL} {TIMEFRAME} | Cash: {acc.cash:.2f} USDT | Strg+C beendet")
    while True:
        try:
            df = pd.DataFrame(ex.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=TREND_LEN + 50),
                              columns=["timestamp", "open", "high", "low", "close", "volume"])
            df = indicators(df)
            price = df["close"].iloc[-1]
            closed = df.iloc[-2]                      # letzte ABGESCHLOSSENE Kerze
            if acc.qty and price <= acc.entry * (1 - STOP_LOSS):
                acc.sell(price, int(df["timestamp"].iloc[-1]), "Stop Loss")
            if closed["timestamp"] != last_ts:
                last_ts = int(closed["timestamp"])
                if acc.qty:
                    acc.held += 1
                s = signal(closed, acc.qty > 0, acc.held)
                if s == "buy":
                    acc.buy(price, last_ts)
                elif s == "sell":
                    acc.sell(price, last_ts, "Signal")
                print(f"{datetime.now():%H:%M}  Kurs {price:.2f}  RSI {closed['rsi']:.1f}  "
                      f"Depotwert {acc.value(price):.2f} USDT")
            json.dump({**acc.__dict__, "last_ts": last_ts}, open(STATE_FILE, "w"))
        except ccxt.NetworkError as e:
            print("Netzwerkfehler, neuer Versuch gleich:", e)
        except KeyboardInterrupt:
            sys.exit(0)
        time.sleep(60)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["backtest", "paper"])
    p.add_argument("--csv")
    p.add_argument("--bars", type=int, default=24 * 365)
    p.add_argument("--quiet", action="store_true", help="einzelne Trades nicht anzeigen")
    a = p.parse_args()
    QUIET = a.quiet
    if a.mode == "backtest":
        backtest(pd.read_csv(a.csv) if a.csv else fetch(a.bars))
    else:
        paper()
