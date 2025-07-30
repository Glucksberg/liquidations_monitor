#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for telethon import and basic functionality
"""

import os
import sys

# Load environment variables
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

print("🧪 Testando importação do telethon...")
print(f"🔍 Python version: {sys.version}")
print(f"🔍 Python path: {sys.executable}")

try:
    import telethon
    print(f"✅ Telethon importado: {telethon.__version__}")
except ImportError as e:
    print(f"❌ Erro importando telethon: {e}")
    sys.exit(1)

try:
    from telethon import TelegramClient
    print("✅ TelegramClient importado com sucesso")
except ImportError as e:
    print(f"❌ Erro importando TelegramClient: {e}")
    sys.exit(1)

# Check credentials
TELEGRAM_API_ID = os.getenv('TELEGRAM_API_ID')
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')

print(f"🔍 API_ID: {'✅' if TELEGRAM_API_ID else '❌'}")
print(f"🔍 API_HASH: {'✅' if TELEGRAM_API_HASH else '❌'}")

if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
    print("❌ Credenciais não encontradas no .env")
    sys.exit(1)

print("✅ Todas as verificações passaram!")
print("🚀 Telethon está funcionando corretamente")