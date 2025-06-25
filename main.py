import os, time, yfinance as yf, pendulum
import pandas as pd
from ta.momentum import RSIIndicator
from telegram import Bot
import json  # ✅ Make sure this is included

def load_config():
    with open("config.json") as f:
        return json.load(f)

def prompt_override(cfg):
    if os.environ.get("RENDER") == "true":
        print("Running on Render — skipping manual override.")
        return cfg
    try:
        c = input("Override config values? (y/n): ").strip().lower()
    except EOFError:
        return cfg
    if c != 'y': return cfg
    cfg['rsi']['overbought'] = int(input("RSI overbought: "))
    cfg['rsi']['oversold'] = int(input("RSI oversold: "))
    cfg['active_hours_ist']['start'] = input("IST start (HH:MM): ")
    cfg['active_hours_ist']['end'] = input("IST end (HH:MM): ")
    n = int(input("Number of FX pairs: "))
    cfg['pairs'] = []
    for _ in range(n):
        sym = input("Symbol (e.g. EURUSD=X): ")
        tf = input("Timeframe (e.g. 1m,5m): ")
        cfg['pairs'].append({"symbol": sym, "timeframe": tf})
    with open("config.json","w") as f:
        json.dump(cfg, f, indent=2)
    return cfg

def in_active_time(cfg):
    now_ist = pendulum.now("Asia/Kolkata")
    if now_ist.weekday() >= 5: return False
    start = pendulum.parse(cfg['active_hours_ist']['start'], tz="Asia/Kolkata")
    end = pendulum.parse(cfg['active_hours_ist']['end'], tz="Asia/Kolkata")
    return start <= now_ist <= end

def send_telegram(bot, chat_id, msg):
    bot.send_message(chat_id=chat_id, text=msg)

def check_pair(bot, chat_id, rsi_cfg, pair):
    sym, tf = pair['symbol'], pair['timeframe']
    df = yf.download(sym, period="60m", interval=tf)
    if df.empty:
        print(f"No data returned for {sym} at {tf}")
        return
    rsi = RSIIndicator(df['Close'], window=rsi_cfg['period']).rsi().iloc[-1]
    stat = None
    if rsi > rsi_cfg['overbought']:
        stat="OVERBOUGHT"
    elif rsi < rsi_cfg['oversold']:
        stat="OVERSOLD"
    if stat:
        send_telegram(bot, chat_id, f"⚠️ RSI {rsi:.2f} on {sym} ({tf}) → {stat}")

def main():
    cfg = load_config()
    cfg = prompt_override(cfg)
    bot = Bot(cfg['telegram']['bot_token'])
    chat_id = cfg['telegram']['chat_id']
    while True:
        if in_active_time(cfg):
            for pair in cfg['pairs']:
                try:
                    check_pair(bot, chat_id, cfg['rsi'], pair)
                except Exception as e:
                    print("Error:", e)
        else:
            print("Outside IST active hours or weekend.")
        time.sleep(60)

if __name__ == "__main__":
    main()
