#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integrated Monitor - Binance & Bybit
Real-time liquidation tracker for cryptocurrency exchanges
"""

import json
import time
import threading
import websocket
import requests
import os
from datetime import datetime, timezone

# Load environment variables from .env file
def load_env_file():
    try:
        with open('.env', 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    except FileNotFoundError:
        print("Warning: .env file not found")

load_env_file()

# Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID') 

# Special tracked symbols
TRACKED_SYMBOLS = {"BTCUSDT", "ETHUSDT", "ETHUSDC", "SOLUSDT"}
SYMBOL_COLORS = {"BTC": "🟠", "ETH": "🔵", "SOL": "🟣"}

def send_telegram(message: str):
    """Send message to Telegram"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        resp = requests.post(url, json={
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "MarkdownV2"
        }, timeout=10)
        if resp.status_code == 200:
            print(f"✅ Telegram: {message[:50]}...")
        else:
            print(f"❌ Telegram Error: {resp.status_code}")
    except Exception as e:
        print(f"❌ Telegram Exception: {e}")

def md_escape(text: str) -> str:
    """Escape characters for MarkdownV2"""
    for ch in r"\_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, f"\\{ch}")
    return text

def skulls(value: float, step: int = 1_000_000) -> str:
    return "💀" * int(value // step)

def base_format(symbol, side, value, price, exchange_tag):
    """Format for special symbols (BTC, ETH, SOL)"""
    asset = symbol.replace("USDT", "").replace("USDC", "")
    emoji = SYMBOL_COLORS.get(asset, "")
    position = "SHORT" if side == "BUY" or side == "Buy" else "LONG"
    v_fmt = md_escape(f"${value:,.2f}")
    p_fmt = md_escape(f"{price:,.2f}")
    
    skull_line = skulls(value)
    if skull_line:
        return (
            f"{skull_line}\n"
            f"*{exchange_tag} Liquidation\\!*\n"
            f"{position} {emoji}${asset}\n"
            f"*{v_fmt} @ {p_fmt}*"
        )
    else:
        return (
            f"*{exchange_tag} Liquidation\\!*\n"
            f"{position} {emoji}${asset}\n"
            f"*{v_fmt} @ {p_fmt}*"
        )

def generic_format(symbol, side, value, price, exchange_tag):
    """Format for other symbols (above 500k)"""
    position = "SHORT" if side == "BUY" or side == "Buy" else "LONG"
    s = md_escape(symbol)
    v_fmt = md_escape(f"${value:,.2f}")
    p_fmt = md_escape(f"{price:,.2f}")
    
    skull_line = skulls(value)
    if skull_line:
        return (
            f"{skull_line}\n"
            f"*{exchange_tag} Liquidation\\!*\n"
            f"{position} ${s}\n"
            f"*{v_fmt} @ {p_fmt}*"
        )
    else:
        return (
            f"*{exchange_tag} Liquidation\\!*\n"
            f"{position} ${s}\n"
            f"*{v_fmt} @ {p_fmt}*"
        )

class BinanceMonitor:
    def __init__(self):
        self.ws = None
        self.running = False
        self.reconnect_count = 0
        self.max_reconnect_attempts = 10

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            order = data.get('o', {})
            symbol = order.get('s')
            side = order.get('S')
            qty = float(order.get('q', 0))
            price = float(order.get('p', 0))
            value = qty * price

            if not all([symbol, side, qty, price]):
                return

            # Apply filter rules
            if symbol in TRACKED_SYMBOLS and value >= 500_000:
                alert = base_format(symbol, side, value, price, "🔶 Binance")
                print(f"🚨 Binance Special: {symbol} ${value:,.2f}")
                send_telegram(alert)
            elif value >= 500_000:
                alert = generic_format(symbol, side, value, price, "🔶 Binance")
                print(f"🚨 Binance Generic: {symbol} ${value:,.2f}")
                send_telegram(alert)

        except Exception as e:
            print(f"❌ Binance error: {e}")

    def on_error(self, ws, error):
        print(f"❌ Binance WebSocket error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print(f"⚠️ Binance connection closed: {close_status_code}")
        if self.running and self.reconnect_count < self.max_reconnect_attempts:
            self.reconnect_count += 1
            print(f"🔄 Binance reconnecting... ({self.reconnect_count}/{self.max_reconnect_attempts})")
            time.sleep(5)  # Wait 5 seconds before reconnecting
            self.start()

    def on_open(self, ws):
        print("🟢 Binance connected")
        self.reconnect_count = 0  # Reset reconnect counter on successful connection

    def start(self):
        self.running = True
        self.ws = websocket.WebSocketApp(
            "wss://fstream.binance.com/ws/!forceOrder@arr",
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        
        # Ping thread to maintain connection
        def ping_loop():
            while self.running:
                time.sleep(30)
                try:
                    if self.ws and hasattr(self.ws, 'sock') and self.ws.sock:
                        self.ws.sock.ping()
                        print("💓 Binance ping")
                except:
                    break
        
        threading.Thread(target=ping_loop, daemon=True).start()
        self.ws.run_forever()

class BybitMonitor:
    def __init__(self):
        self.ws = None
        self.running = False
        self.reconnect_count = 0

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            
            if 'success' in data and data.get('op') == 'subscribe':
                print(f"✅ Bybit subscription confirmed")
                
            elif 'topic' in data and data['topic'].startswith('allLiquidation'):
                for liq_data in data.get('data', []):
                    symbol = liq_data.get('s', '')
                    side = liq_data.get('S', '')
                    size = float(liq_data.get('v', 0))
                    price = float(liq_data.get('p', 0))
                    value = size * price
                    
                    # Apply filter rules
                    if symbol in TRACKED_SYMBOLS and value >= 500_000:
                        alert = base_format(symbol, side, value, price, "🟨 Bybit")
                        print(f"🚨 Bybit Special: {symbol} ${value:,.2f}")
                        send_telegram(alert)
                    elif value >= 500_000:
                        alert = generic_format(symbol, side, value, price, "🟨 Bybit")
                        print(f"🚨 Bybit Generic: {symbol} ${value:,.2f}")
                        send_telegram(alert)
                        
        except Exception as e:
            print(f"❌ Bybit error: {e}")

    def on_error(self, ws, error):
        print(f"❌ Bybit WebSocket error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print(f"⚠️ Bybit connection closed: {close_status_code}")

    def on_open(self, ws):
        print("🟢 Bybit connected")
        # Subscribe to all symbols (to capture liquidations >500k)
        bybit_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "DOGEUSDT", "XRPUSDT", "AVAXUSDT", "DOTUSDT", "MATICUSDT", "LINKUSDT"]
        args = [f"allLiquidation.{s}" for s in bybit_symbols]
        subscribe_msg = {"op": "subscribe", "args": args}
        ws.send(json.dumps(subscribe_msg))
        print(f"🔔 Bybit subscribed to: {bybit_symbols}")

    def start(self):
        self.running = True
        self.ws = websocket.WebSocketApp(
            "wss://stream.bybit.com/v5/public/linear",
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        
        # Ping thread to maintain connection
        def ping_loop():
            while self.running:
                time.sleep(30)
                try:
                    if self.ws and hasattr(self.ws, 'sock') and self.ws.sock:
                        self.ws.send(json.dumps({"op": "ping"}))
                        print("💓 Bybit ping")
                except:
                    break
        
        threading.Thread(target=ping_loop, daemon=True).start()
        self.ws.run_forever()

def main():
    print("🚀 Starting Integrated Monitor...")
    print(f"📊 Special Symbols: {TRACKED_SYMBOLS} (≥$500k)")
    print(f"💰 Generic Threshold: ≥$500k")
    
    # Send startup message
    start_msg = f"🚀 *Integrated Monitor Active*\n📊 BTC, ETH, SOL: ≥$500k\n💰 Others: ≥$500k"
    send_telegram(start_msg)
    
    # Start monitors in separate threads
    binance_monitor = BinanceMonitor()
    bybit_monitor = BybitMonitor()
    
    binance_thread = threading.Thread(target=binance_monitor.start, daemon=True)
    bybit_thread = threading.Thread(target=bybit_monitor.start, daemon=True)
    
    binance_thread.start()
    bybit_thread.start()
    
    try:
        # Keep main process alive
        while True:
            time.sleep(60)
            print("💓 Monitor alive")
    except KeyboardInterrupt:
        print("🛑 Stopping monitors...")
        binance_monitor.running = False
        bybit_monitor.running = False

if __name__ == "__main__":
    main()