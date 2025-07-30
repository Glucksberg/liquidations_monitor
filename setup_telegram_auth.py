#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Setup script for Telegram authentication
Run this once to create the session file
"""

import os
import asyncio
from telethon import TelegramClient

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

async def setup_auth():
    """Setup Telegram authentication"""
    TELEGRAM_API_ID = os.getenv('TELEGRAM_API_ID')
    TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')
    
    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        print("❌ TELEGRAM_API_ID ou TELEGRAM_API_HASH não encontrados no .env")
        return
    
    print("🔐 Configurando autenticação do Telegram...")
    print("📱 Você receberá um código no Telegram")
    print("🔑 Digite sua senha 2FA se tiver ativada")
    
    try:
        # Create client with session
        client = TelegramClient('hyperliquid_session', TELEGRAM_API_ID, TELEGRAM_API_HASH)
        
        # Start client (this will prompt for authentication)
        await client.start()
        
        print("✅ Autenticação concluída!")
        print("📁 Arquivo de sessão criado: hyperliquid_session.session")
        print("🚀 Agora você pode usar o PM2 sem problemas")
        
        # Test connection
        me = await client.get_me()
        print(f"👤 Conectado como: {me.first_name} (@{me.username})")
        
        await client.disconnect()
        
    except Exception as e:
        print(f"❌ Erro na autenticação: {e}")

if __name__ == "__main__":
    asyncio.run(setup_auth()) 