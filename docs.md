# Liquidations Monitor - Real-time Exchange Liquidation Tracker

## Overview

The **Liquidations Monitor** is a real-time liquidation monitoring system for **Binance** and **Bybit** exchanges. The application monitors WebSocket feeds from both exchanges and sends formatted alerts to a Telegram channel when significant liquidations occur.

## Detailed Operation

### 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Binance WS    │    │   Bybit WS      │    │  Telegram Bot   │
│  Liquidations   │    │  Liquidations   │    │    Channel      │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          ▼                      ▼                      ▲
    ┌─────────────────────────────────────────────────────┴─────┐
    │              Liquidations Monitor                         │
    │  • Processes liquidation data                            │
    │  • Applies value filters                                 │
    │  • Formats MarkdownV2 messages                           │
    │  • Sends to Telegram                                     │
    └───────────────────────────────────────────────────────────┘
```

### 📡 WebSocket Connections

#### Binance
- **Endpoint**: `wss://fstream.binance.com/ws/!forceOrder@arr`
- **Type**: Global forced liquidation stream
- **Data Format**: 
  ```json
  {
    "o": {
      "s": "BTCUSDT",    // Symbol
      "S": "BUY",        // Side  
      "q": "0.001",      // Quantity
      "p": "50000.00"    // Price
    }
  }
  ```

#### Bybit  
- **Endpoint**: `wss://stream.bybit.com/v5/public/linear`
- **Type**: Subscription to specific liquidation topics
- **Subscription**: `allLiquidation.{SYMBOL}` for each monitored symbol
- **Data Format**:
  ```json
  {
    "topic": "allLiquidation.BTCUSDT",
    "data": [{
      "s": "BTCUSDT",    // Symbol
      "S": "Buy",        // Side
      "v": "0.001",      // Volume (executed size)
      "p": "50000.00"    // Price (bankruptcy price)
    }]
  }
  ```

### 🎯 Filters and Thresholds

#### Special Monitored Symbols
```python
TRACKED_SYMBOLS = {"BTCUSDT", "ETHUSDT", "ETHUSDC", "SOLUSDT"}
```

#### Thresholds by Exchange

**Both Binance & Bybit:**
- Special symbols (BTC, ETH, SOL): ≥ **$50,000**
- Other symbols: ≥ **$500,000**

### 💬 Message Formatting

#### Telegram MarkdownV2
The bot uses **MarkdownV2** formatting which requires escaping special characters:
- Characters that need escaping: `\_*[]()~\`>#+-=|{}.!`
- Automatically applied by the `md_escape()` function

#### Message Structure

**For special symbols (BTC, ETH, SOL):**
```
💀💀💀 *🔶 Binance Liquidated!* LONG 🟠$BTC
*$123,456.78 @ 67,890.12*
`2025-01-17 15:30:45 UTC`
```

**For other symbols:**
```
💀💀 *🟨 Bybit Liquidated!* SHORT $ADAUSDT  
*$87,654.32 @ 0.4521*
`2025-01-17 15:30:45 UTC`
```

#### Visual Elements
- **Skulls (💀)**: Quantity based on value (1 skull per $100k)
- **Exchange Tags**: 🔶 Binance / 🟨 Bybit
- **Crypto Colors**: 🟠 BTC / 🔵 ETH / 🟣 SOL
- **Position**: SHORT (for BUY orders) / LONG (for SELL orders)

### ⚙️ Configuration

#### Environment Variables
```bash
# .env file
BOT_TOKEN=your_telegram_bot_token_here
CHAT_ID=your_telegram_chat_id_here
```

#### Main Variables
```python
# Tracked symbols and colors
TRACKED_SYMBOLS = {"BTCUSDT", "ETHUSDT", "ETHUSDC", "SOLUSDT"}
SYMBOL_COLORS = {"BTC": "🟠", "ETH": "🔵", "SOL": "🟣"}
```

### 🔄 Execution and Deployment

#### Virtual Environment
```bash
# Activate environment
source venv/bin/activate

# Main dependencies
pip install websocket-client requests
```

#### Manual Execution
```bash
python3 integrated_monitor.py
```

#### PM2 Execution
```bash
pm2 start ecosystem.config.js
pm2 logs integrated_monitor
pm2 restart integrated_monitor
```

#### PM2 Configuration (ecosystem.config.js)
```javascript
module.exports = {
  apps: [{
    name: "integrated_monitor",
    script: "integrated_monitor.py", 
    interpreter: "venv/bin/python",
    autorestart: true,
    watch: false,
    max_memory_restart: "500M",
    log_date_format: "YYYY-MM-DD HH:mm:ss"
  }]
};
```

### 🐛 Known Issues and Solutions

#### 1. **Bybit not showing liquidations**
- **Possible cause**: Subscription may not be active
- **Solution**: Check logs for subscription confirmation messages
- **Debug**: Monitor connection logs for WebSocket status

#### 2. **MarkdownV2 Error - Unescaped characters**
- **Symptom**: `Bad Request: can't parse entities: Character '.' is reserved`
- **Solution**: `md_escape()` function applied to all dynamic texts
- **Special attention**: Timestamps contain `:-` that need escaping

#### 3. **WebSocket ping_interval not supported**
- **Symptom**: `TypeError: WebSocketApp.__init__() got an unexpected keyword argument 'ping_interval'`
- **Solution**: Remove `ping_interval` parameter from WebSocket creation
- **Compatible version**: websocket-client 1.8.0

### 📊 Monitoring and Logs

#### Log Files
- PM2 automatically handles logging
- View logs with: `pm2 logs integrated_monitor`

#### Status Verification
```bash
# Check running processes
pm2 list

# Real-time logs
pm2 logs integrated_monitor --lines 50

# Restart if needed
pm2 restart integrated_monitor
```

### 🚀 Production Setup

#### Auto-restart on Server Reboot
```bash
# Setup PM2 startup
pm2 startup
# Follow the command output instructions

# Save current process list
pm2 save
```

#### Security Best Practices
- Never commit `.env` file to repository
- Use `.env.example` as template
- Rotate bot tokens periodically
- Monitor for unauthorized access

---

## 🔧 Implementation Features

### Current Implementation
The system uses an integrated monitor that handles both exchanges in separate threads:

- **Class-based Architecture**: `BinanceMonitor` and `BybitMonitor` classes
- **Automatic Reconnection**: Built-in reconnection handling
- **Ping Management**: Automatic ping for Bybit connection stability
- **Dual Threshold System**: $50k for special symbols, $500k for others
- **Visual Feedback**: Skull emojis (1 per $100k) and color-coded symbols

### Performance Characteristics
- **Memory Usage**: ~20MB typical
- **CPU Usage**: <1% typical
- **Network**: Persistent WebSocket connections
- **Reliability**: Auto-restart on failure, systemd integration

---

*Documentation created: July 17, 2025*  
*Last update: Production-ready Integrated Monitor v1.0*