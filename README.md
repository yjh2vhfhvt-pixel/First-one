# Krypto Paper Trading Bot

Handelt BTC/USDT mit **Spielgeld** (1000 USDT) auf echten Live Kursen von Binance. Kein Konto und kein API Key nötig.

## Strategie (Mean Reversion)
- **Kauf:** RSI(14) unter 30 (überverkauft) und Kurs über dem 200er Durchschnitt (kein Kauf in einem Crash)
- **Verkauf:** RSI über 55, spätestens nach 72 Stunden
- **Stop Loss:** 4 % unter Kaufpreis
- Pro Trade werden 25 % des Kapitals eingesetzt, 0,1 % Gebühren sind eingerechnet

## Starten
```
pip install -r requirements.txt
python bot.py backtest --quiet    # letztes Jahr testen
python bot.py paper               # live mit Spielgeld, Strg+C beendet
```
Trades landen in `trades.csv`, der Stand in `paper_state.json` (bleibt nach Neustart erhalten).
Alle Einstellungen stehen oben in `bot.py`.

## Wichtig
Ein gutes Backtest Ergebnis heißt nicht, dass der Bot in Zukunft Gewinn macht. Erst mehrere Wochen mit Spielgeld laufen lassen.
