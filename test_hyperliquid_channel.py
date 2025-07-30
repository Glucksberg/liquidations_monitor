#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to check Hyperliquid channel access
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

async def test_channel_access():
    """Test access to Hyperliquid channel"""
    TELEGRAM_API_ID = os.getenv('TELEGRAM_API_ID')
    TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')
    
    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        print("❌ Credenciais não encontradas")
        return
    
    print("🔍 Testando acesso ao canal Hyperliquid...")
    
    try:
        # Create client
        client = TelegramClient('test_session', TELEGRAM_API_ID, TELEGRAM_API_HASH)
        await client.start()
        print("✅ Client conectado")
        
        # Try to access channel
        channel_username = 'hyperliquid_liquidations'
        
        try:
            # Try with @ prefix
            channel = await client.get_entity(f"@{channel_username}")
            print(f"✅ Canal encontrado: @{channel_username}")
        except Exception as e:
            print(f"❌ Erro com @: {e}")
            try:
                # Try without @
                channel = await client.get_entity(channel_username)
                print(f"✅ Canal encontrado: {channel_username}")
            except Exception as e2:
                print(f"❌ Erro sem @: {e2}")
                return
        
        print(f"📊 Canal: {channel.title}")
        print(f"🔍 ID: {channel.id}")
        print(f"👥 Membros: {getattr(channel, 'participants_count', 'N/A')}")
        
        # Get recent messages
        print("\n📝 Últimas 5 mensagens:")
        message_count = 0
        async for message in client.iter_messages(channel, limit=5):
            if message.message:
                message_count += 1
                print(f"\n--- Mensagem {message_count} ---")
                print(f"📅 Data: {message.date}")
                print(f"📝 Texto: {message.message[:200]}...")
                
                # Test our parsing
                from integrated_monitor import parse_hyperliquid_message
                parsed = parse_hyperliquid_message(message.message)
                if parsed:
                    print(f"✅ Parse OK: {parsed}")
                else:
                    print("❌ Parse falhou")
        
        print(f"\n📊 Total de mensagens encontradas: {message_count}")
        
        await client.disconnect()
        print("✅ Teste concluído")
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_channel_access()) 