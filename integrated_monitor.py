#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integrated Monitor - Binance & Bybit & Hyperliquid
Real-time liquidation tracker for cryptocurrency exchanges
"""

import json
import time
import threading
import websocket
import requests
import os
import re
import asyncio
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

# Hyperliquid Telegram Monitor Configuration
TELEGRAM_API_ID = os.getenv('TELEGRAM_API_ID')
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')
HYPERLIQUID_CHANNEL = 'hyperliquid_liquidations'  # Canal a ser monitorado

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

def format_value_compact(value: float) -> str:
    """Format value in compact format: $2.16M, $542.3k"""
    if value >= 1_000_000:
        return f"${round(value / 1_000_000, 2):.2f}M"
    elif value >= 1_000:
        return f"${round(value / 1_000, 1):.1f}k"
    else:
        return f"${value:.2f}"

def base_format(symbol, side, value, price, exchange_tag):
    """Format for special symbols (BTC, ETH, SOL)"""
    asset = symbol.replace("USDT", "").replace("USDC", "")
    emoji = SYMBOL_COLORS.get(asset, "")
    position = "SHORT" if side == "BUY" or side == "Buy" else "LONG"
    v_fmt = md_escape(format_value_compact(value))
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
    v_fmt = md_escape(format_value_compact(value))
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

def parse_hyperliquid_message(message_text):
    """Parse Hyperliquid liquidation message and extract relevant data"""
    # Pattern to match: 🔴/🟢 #SYMBOL Long/Short Liquidation: $VALUE @ $PRICE
    # Updated to handle both 🔴 (Long) and 🟢 (Short) liquidations
    pattern = r'[🔴🟢]\s*#(\w+)\s+(Long|Short)\s+Liquidation:\s*\$([0-9,.kM]+)\s*@\s*\$([0-9,.]+)'
    
    match = re.search(pattern, message_text)
    if match:
        symbol = match.group(1)      # SOL, ETH, ENA, BTC, etc
        side = match.group(2)        # Long, Short  
        value_str = match.group(3)   # 76.63k, 79.75k, 23.44M, etc
        price_str = match.group(4)   # 179.50, 3764.0, 117,078.5, etc
        
        # Convert value from string (handle 'k' and 'M' suffixes)
        if value_str.endswith('M'):
            value = float(value_str.replace('M', '').replace(',', '')) * 1_000_000
        elif value_str.endswith('k'):
            value = float(value_str.replace('k', '').replace(',', '')) * 1000
        else:
            value = float(value_str.replace(',', ''))
            
        return {
            'symbol': symbol,
            'side': side,
            'value': value,
            'value_display': value_str,  # Keep original format for display
            'price': price_str
        }
    return None

def format_hyperliquid_message(parsed_data):
    """Format Hyperliquid message in our channel style"""
    symbol = parsed_data['symbol']
    side = parsed_data['side'].upper()
    value_display = parsed_data['value_display']
    price = parsed_data['price']
    value = parsed_data['value']
    
    # Apply symbol colors and formatting based on your examples
    if symbol == 'SOL':
        symbol_display = '🟣$SOL'
    elif symbol == 'ETH':
        symbol_display = '🔵$ETH'
    elif symbol == 'BTC':
        symbol_display = '🟠$BTC'
    else:
        # For other symbols like ENA, keep as is without USDT suffix
        symbol_display = f'${symbol}'
    
    # Calculate skulls (1 skull per 1 million)
    skulls_count = int(value // 1_000_000)
    skull_line = "💀" * skulls_count if skulls_count > 0 else ""
    
    # Escape special characters for MarkdownV2
    value_escaped = md_escape(f"${value_display}")
    price_escaped = md_escape(f"${price}")
    
    # Format with skulls if applicable
    if skull_line:
        formatted = (
            f"{skull_line}\n"
            f"💦 *Hyperliquid Liquidation\\!*\n"
            f"{side} {symbol_display}\n"
            f"*{value_escaped} @ {price_escaped}*"
        )
    else:
        formatted = (
            f"💦 *Hyperliquid Liquidation\\!*\n"
            f"{side} {symbol_display}\n"
            f"*{value_escaped} @ {price_escaped}*"
        )
    
    return formatted

def test_hyperliquid_parsing():
    """Test function to verify parsing works with real examples"""
    test_messages = [
        "🔴 #SOL Long Liquidation: $76.63k @ $179.50 [scan] (https://hypurrscan.io/address/0x482db931ca05d474adf272f81c5038e8aa5071a6)[dash] (https://hyperdash.info/trader/0x482db931ca05d474adf272f81c5038e8aa5071a6)",
        "🔴 #ETH Long Liquidation: $79.75k @ $3,764.0 [scan] (https://hypurrscan.io/address/0x57a0d8048a3aa882ac1aa7f1378fe2d453e26fb2)[dash] (https://hyperdash.info/trader/0x57a0d8048a3aa882ac1aa7f1378fe2d453e26fb2)",
        "🔴 #ENA Long Liquidation: $97.93k @ $0.5637 [scan] (https://hypurrscan.io/address/0xbbb23927fa6ac11fb668439bec8682ffac036125)[dash] (https://hyperdash.info/trader/0xbbb23927fa6ac11fb668439bec8682ffac036125)",
        "🔴 #BTC Long Liquidation: $23.44M @ $117,078.5 [scan] (https://hypurrscan.io/address/0x1f250df59a777d61cb8bd043c12970f3afe4f925)[dash] (https://hyperdash.info/trader/0x1f250df59a777d61cb8bd043c12970f3afe4f925)",
        "🟢 #ETH Short Liquidation: $160.42k @ $3,806.3 [scan][dash]"
    ]
    
    print("🧪 Testando parser da Hyperliquid...")
    for i, msg in enumerate(test_messages, 1):
        print(f"\n--- Teste {i} ---")
        print(f"Input: {msg[:100]}...")
        
        parsed = parse_hyperliquid_message(msg)
        if parsed:
            print(f"✅ Parsed: {parsed}")
            formatted = format_hyperliquid_message(parsed)
            print(f"📤 Output: {formatted}")
            
            # Test filter
            value = parsed['value']
            if value >= 1_000_000:
                print(f"✅ Filtro: Passou (${value:,.2f} >= $1M)")
            else:
                print(f"❌ Filtro: Bloqueado (${value:,.2f} < $1M)")
        else:
            print("❌ Parsing falhou")
    
    print("\n🧪 Teste concluído\n")

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
            if symbol in TRACKED_SYMBOLS and value >= 1_000_000:
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
        self.max_reconnect_attempts = 10
        self.last_ping_time = 0
        self.connection_alive = False

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            
            # Update connection status on any message
            self.connection_alive = True
            self.last_ping_time = time.time()
            
            if 'success' in data and data.get('op') == 'subscribe':
                print(f"✅ Bybit subscription confirmed")
                
            elif data.get('op') == 'pong':
                print("💓 Bybit pong received")
                
            elif 'topic' in data and data['topic'].startswith('allLiquidation'):
                for liq_data in data.get('data', []):
                    symbol = liq_data.get('s', '')
                    side = liq_data.get('S', '')
                    size = float(liq_data.get('v', 0))
                    price = float(liq_data.get('p', 0))
                    value = size * price
                    
                    # Apply filter rules
                    if symbol in TRACKED_SYMBOLS and value >= 1_000_000:
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
        self.connection_alive = False
        if self.running and self.reconnect_count < self.max_reconnect_attempts:
            self.reconnect_count += 1
            print(f"🔄 Bybit reconnecting... ({self.reconnect_count}/{self.max_reconnect_attempts})")
            time.sleep(5)  # Wait 5 seconds before reconnecting
            self.start()

    def on_open(self, ws):
        print("🟢 Bybit connected")
        self.reconnect_count = 0  # Reset reconnect counter on successful connection
        self.connection_alive = True
        self.last_ping_time = time.time()
        
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
        
        # Enhanced ping and connection monitoring thread
        def enhanced_monitoring_loop():
            while self.running:
                time.sleep(30)
                current_time = time.time()
                
                try:
                    # Check if connection is still alive
                    if self.ws and hasattr(self.ws, 'sock') and self.ws.sock:
                        # Send ping
                        self.ws.send(json.dumps({"op": "ping"}))
                        print("💓 Bybit ping")
                        
                        # Check if we haven't received any message in the last 2 minutes
                        if current_time - self.last_ping_time > 120:
                            print("⚠️ Bybit: No response for 2 minutes, connection may be dead")
                            self.connection_alive = False
                            
                            # Force reconnection
                            if self.ws and hasattr(self.ws, 'sock'):
                                try:
                                    self.ws.close()
                                except:
                                    pass
                            break
                    else:
                        print("⚠️ Bybit: WebSocket connection lost")
                        self.connection_alive = False
                        break
                        
                except Exception as e:
                    print(f"❌ Bybit monitoring error: {e}")
                    self.connection_alive = False
                    break
        
        threading.Thread(target=enhanced_monitoring_loop, daemon=True).start()
        self.ws.run_forever()
    
    def force_reconnect(self):
        """Force a reconnection if the current connection seems dead"""
        print("🔄 Bybit: Forcing reconnection...")
        self.connection_alive = False
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
        # The on_close handler will trigger automatic reconnection
    
    def is_healthy(self):
        """Check if the connection is healthy"""
        current_time = time.time()
        return (self.connection_alive and 
                self.ws and 
                hasattr(self.ws, 'sock') and 
                self.ws.sock and
                current_time - self.last_ping_time < 120)

class HyperliquidMonitor:
    """Monitor Hyperliquid Liquidations Telegram channel"""
    
    def __init__(self):
        self.client = None
        self.running = False
    
    async def setup_client(self):
        """Setup Telegram client with proper imports and error handling"""
        try:
            print("🔍 Hyperliquid: Tentando importar telethon...")
            import sys
            print(f"🔍 Python path: {sys.path}")
            
            try:
                import telethon
                print(f"✅ Telethon importado: {telethon.__version__}")
            except ImportError as ie:
                print(f"❌ Erro importando telethon: {ie}")
                return False
            
            from telethon import TelegramClient
            print("✅ TelegramClient importado com sucesso")
            
            if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
                print("❌ Hyperliquid: Missing TELEGRAM_API_ID or TELEGRAM_API_HASH in .env")
                print(f"🔍 API_ID: {'✅' if TELEGRAM_API_ID else '❌'}")
                print(f"🔍 API_HASH: {'✅' if TELEGRAM_API_HASH else '❌'}")
                return False
                
            print(f"🔍 Usando API_ID: {TELEGRAM_API_ID[:5]}...")
            print(f"🔍 Usando API_HASH: {TELEGRAM_API_HASH[:5]}...")
                
            # Use session file that should be created by previous authentication
            session_name = 'hyperliquid_session'
            self.client = TelegramClient(session_name, TELEGRAM_API_ID, TELEGRAM_API_HASH)
            
            # Try to start with existing session or interactive auth
            try:
                # For manual execution, allow interactive auth
                import sys
                if sys.stdin.isatty():  # Running interactively (not via PM2)
                    print("🔄 Hyperliquid: Iniciando autenticação interativa...")
                    await self.client.start()
                    print("🟢 Hyperliquid Telegram client connected (interactive)")
                    return True
                else:
                    # For PM2, try non-interactive
                    await self.client.connect()
                    if await self.client.is_user_authorized():
                        print("🟢 Hyperliquid Telegram client connected (existing session)")
                        return True
                    else:
                        print("❌ Hyperliquid: Sessão não autorizada")
                        print("💡 Execute 'python integrated_monitor.py' diretamente primeiro para autenticar")
                        await self.client.disconnect()
                        return False
            except Exception as auth_error:
                print(f"❌ Erro de autenticação: {auth_error}")
                print("💡 Execute 'python integrated_monitor.py' diretamente primeiro para autenticar")
                try:
                    await self.client.disconnect()
                except:
                    pass
                return False
            
        except ImportError as ie:
            print(f"❌ Hyperliquid: telethon not installed. Run: pip install telethon")
            print(f"❌ Erro detalhado: {ie}")
            return False
        except Exception as e:
            print(f"❌ Hyperliquid setup error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def handle_new_message(self, event):
        """Process new messages from Hyperliquid channel"""
        try:
            print(f"🎯 Hyperliquid: Event handler chamado!")
            print(f"🔍 Event type: {type(event)}")
            
            message_text = event.message.message
            print(f"🔍 Hyperliquid: Nova mensagem recebida: {message_text[:100]}...")
            
            if not message_text:
                print("⚠️ Hyperliquid: Mensagem vazia")
                return
                
            # Parse liquidation message
            parsed = parse_hyperliquid_message(message_text)
            if parsed:
                print(f"✅ Hyperliquid: Mensagem parseada: {parsed}")
                
                # Apply filter: only show liquidations >= $1M
                value = parsed['value']
                if value < 1_000_000:
                    print(f"❌ Hyperliquid: Liquidação filtrada (${value:,.2f} < $1M)")
                    return
                
                # Format message in our style
                formatted_msg = format_hyperliquid_message(parsed)
                
                # Send to our channel
                send_telegram(formatted_msg)
                
                # Log the activity
                symbol = parsed['symbol']
                print(f"🚨 Hyperliquid: {symbol} ${value:,.2f}")
            else:
                print(f"❌ Hyperliquid: Não foi possível parsear: {message_text}")
                
        except Exception as e:
            print(f"❌ Hyperliquid message error: {e}")
            import traceback
            traceback.print_exc()
    
    async def start_monitoring(self):
        """Start monitoring the Hyperliquid channel"""
        try:
            print("🔄 Hyperliquid: Iniciando setup do client...")
            if not await self.setup_client():
                print("❌ Hyperliquid: Falha no setup do client")
                return
                
            print(f"🔍 Hyperliquid: Tentando acessar canal: {HYPERLIQUID_CHANNEL}")
                
            # Get the channel entity - try different formats
            try:
                # Try with @ prefix
                channel = await self.client.get_entity(f"@{HYPERLIQUID_CHANNEL}")
                print(f"✅ Hyperliquid: Canal encontrado com @: @{HYPERLIQUID_CHANNEL}")
            except:
                try:
                    # Try without @ prefix
                    channel = await self.client.get_entity(HYPERLIQUID_CHANNEL)
                    print(f"✅ Hyperliquid: Canal encontrado sem @: {HYPERLIQUID_CHANNEL}")
                except:
                    # Try with t.me link
                    channel = await self.client.get_entity("https://t.me/hyperliquid_liquidations")
                    print(f"✅ Hyperliquid: Canal encontrado via link")
            
            print(f"📡 Hyperliquid: Monitorando canal: {channel.title}")
            print(f"🔍 Canal ID: {channel.id}")
            print(f"🔍 Canal username: {getattr(channel, 'username', 'N/A')}")
            
            # Add event handler for new messages
            from telethon import events
            self.client.add_event_handler(
                self.handle_new_message,
                events.NewMessage(chats=channel)
            )
            
            print("🎯 Hyperliquid: Event handler adicionado")
            
            # Test: Get some recent messages to see format
            print("🔍 Hyperliquid: Verificando mensagens recentes...")
            message_count = 0
            async for message in self.client.iter_messages(channel, limit=10):
                if message.message:
                    message_count += 1
                    print(f"📝 Mensagem {message_count}: {message.message[:150]}...")
                    # Test parsing
                    test_parsed = parse_hyperliquid_message(message.message)
                    if test_parsed:
                        print(f"✅ Parse OK: {test_parsed}")
                    else:
                        print("❌ Parse falhou")
                        
            print(f"📊 Total de mensagens recentes encontradas: {message_count}")
            
            # Keep the client running
            self.running = True
            print("🚀 Hyperliquid: Client ativo, aguardando mensagens...")
            
            # Add periodic check to verify we're still connected
            async def periodic_check():
                while self.running:
                    try:
                        await asyncio.sleep(60)  # Check every minute
                        if self.client and self.client.is_connected():
                            print("💓 Hyperliquid: Client conectado, aguardando...")
                        else:
                            print("⚠️ Hyperliquid: Client desconectado!")
                    except Exception as e:
                        print(f"❌ Hyperliquid periodic check error: {e}")
            
            # Start periodic check
            asyncio.create_task(periodic_check())
            
            await self.client.run_until_disconnected()
            
        except Exception as e:
            print(f"❌ Hyperliquid monitoring error: {e}")
            import traceback
            traceback.print_exc()
    
    def start(self):
        """Start monitoring in asyncio loop"""
        try:
            # Run the async monitoring
            asyncio.run(self.start_monitoring())
        except Exception as e:
            print(f"❌ Hyperliquid start error: {e}")

async def setup_hyperliquid_auth():
    """Setup Hyperliquid authentication interactively if needed"""
    import sys
    if sys.stdin.isatty():  # Running interactively
        print("🔄 Verificando autenticação da Hyperliquid...")
        hyperliquid_monitor = HyperliquidMonitor()
        success = await hyperliquid_monitor.setup_client()
        if success:
            print("✅ Hyperliquid autenticada com sucesso!")
            await hyperliquid_monitor.client.disconnect()
            return True
        else:
            print("❌ Falha na autenticação da Hyperliquid")
            return False
    return True  # Skip for non-interactive (PM2)

def main():
    print("🚀 Starting Integrated Monitor...")
    print(f"📊 Special Symbols: {TRACKED_SYMBOLS} (≥$1M)")
    print(f"💰 Generic Threshold: ≥$500k")
    print(f"📡 Hyperliquid Channel: @{HYPERLIQUID_CHANNEL} (≥$1M)")
    
    # Test Hyperliquid parsing first
    test_hyperliquid_parsing()
    
    # Setup Hyperliquid authentication if running interactively
    import sys
    if sys.stdin.isatty():
        print("\n🔐 Configurando autenticação da Hyperliquid...")
        asyncio.run(setup_hyperliquid_auth())
        print("\n✅ Autenticação concluída. Iniciando monitores...\n")
    
    # Send startup message
    start_msg = f"🚀 *Integrated Monitor Active*\n📊 BTC, ETH, SOL: ≥$1M\n💰 Others: ≥$500k\n📡 Hyperliquid: ≥$1M"
    send_telegram(start_msg)
    
    # Start monitors in separate threads
    binance_monitor = BinanceMonitor()
    bybit_monitor = BybitMonitor()
    hyperliquid_monitor = HyperliquidMonitor()
    
    binance_thread = threading.Thread(target=binance_monitor.start, daemon=True)
    bybit_thread = threading.Thread(target=bybit_monitor.start, daemon=True)
    hyperliquid_thread = threading.Thread(target=hyperliquid_monitor.start, daemon=True)
    
    binance_thread.start()
    bybit_thread.start()
    hyperliquid_thread.start()
    
    try:
        # Enhanced monitoring loop with health checks
        health_check_counter = 0
        while True:
            time.sleep(60)
            health_check_counter += 1
            print("💓 Monitor alive")
            
            # Perform health checks every 5 minutes
            if health_check_counter >= 5:
                health_check_counter = 0
                print("🔍 Performing health checks...")
                
                # Check Bybit health
                if hasattr(bybit_monitor, 'is_healthy') and not bybit_monitor.is_healthy():
                    print("⚠️ Bybit connection appears unhealthy, forcing reconnection...")
                    try:
                        bybit_monitor.force_reconnect()
                    except Exception as e:
                        print(f"❌ Error forcing Bybit reconnection: {e}")
                else:
                    print("✅ Bybit connection healthy")
                
                # Check if threads are still alive
                if not binance_thread.is_alive():
                    print("⚠️ Binance thread died, restarting...")
                    binance_thread = threading.Thread(target=binance_monitor.start, daemon=True)
                    binance_thread.start()
                
                if not bybit_thread.is_alive():
                    print("⚠️ Bybit thread died, restarting...")
                    bybit_thread = threading.Thread(target=bybit_monitor.start, daemon=True)
                    bybit_thread.start()
                
                if not hyperliquid_thread.is_alive():
                    print("⚠️ Hyperliquid thread died, restarting...")
                    hyperliquid_thread = threading.Thread(target=hyperliquid_monitor.start, daemon=True)
                    hyperliquid_thread.start()
                    
    except KeyboardInterrupt:
        print("🛑 Stopping monitors...")
        binance_monitor.running = False
        bybit_monitor.running = False
        hyperliquid_monitor.running = False

if __name__ == "__main__":
    main()