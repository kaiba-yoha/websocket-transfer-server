#!/usr/bin/env python3
"""
シンプルなWebSocketテストクライアント
指定したポートに接続してメッセージを送信する
"""

import asyncio
import json
import logging
import websockets
import sys
import time

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# サーバー設定
SERVER_HOST = "127.0.0.1"
PORT_A = 8675
PORT_B = 8775


async def simple_client(port: int, client_name: str, message: str):
    """シンプルなクライアント"""
    uri = f"ws://{SERVER_HOST}:{port}"
    
    try:
        logger.info(f"{client_name}: {uri}に接続中...")
        
        async with websockets.connect(uri) as websocket:
            logger.info(f"{client_name}: 接続成功!")
            
            # メッセージを送信
            logger.info(f"{client_name}: メッセージ送信 - {message}")
            await websocket.send(message)
            
            # 応答を待機（5秒間）
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                logger.info(f"{client_name}: 応答受信 - {response}")
            except asyncio.TimeoutError:
                logger.info(f"{client_name}: 応答タイムアウト（正常）")
            except Exception as e:
                logger.info(f"{client_name}: 応答受信エラー - {e}")
            
            logger.info(f"{client_name}: テスト完了")
            
    except Exception as e:
        logger.error(f"{client_name}: エラー - {e}")


async def test_port_a():
    """ポート8675のテスト"""
    logger.info("=== ポート8675テスト開始 ===")
    
    test_messages = [
        "Hello from port 8675!",
        "Test message 1",
        "Test message 2",
        json.dumps({"type": "test", "message": "JSON test from 8675", "timestamp": time.time()}),
        json.dumps({"type": "POST", "data": {"command": "test", "message": "UDP test from 8675"}})
    ]
    
    for i, message in enumerate(test_messages):
        await simple_client(PORT_A, f"Client-A-{i+1}", message)
        await asyncio.sleep(1)
    
    logger.info("=== ポート8675テスト完了 ===")


async def test_port_b():
    """ポート8775のテスト"""
    logger.info("=== ポート8775テスト開始 ===")
    
    test_messages = [
        "Hello from port 8775!",
        json.dumps({"type": "test", "message": "JSON test from 8775", "timestamp": time.time()}),
        json.dumps({"type": "POST", "data": {"command": "test", "message": "UDP test from 8775"}})
    ]
    
    for i, message in enumerate(test_messages):
        await simple_client(PORT_B, f"Client-B-{i+1}", message)
        await asyncio.sleep(1)
    
    logger.info("=== ポート8775テスト完了 ===")


async def test_bidirectional():
    """双方向通信テスト"""
    logger.info("=== 双方向通信テスト開始 ===")
    
    # ポート8675に接続
    uri_a = f"ws://{SERVER_HOST}:{PORT_A}"
    uri_b = f"ws://{SERVER_HOST}:{PORT_B}"
    
    try:
        async with websockets.connect(uri_a) as websocket_a, \
                   websockets.connect(uri_b) as websocket_b:
            
            logger.info("両ポートに接続成功!")
            
            # AからBへメッセージ送信
            message_a_to_b = "Message from 8675 to 8775"
            logger.info(f"8675 -> 8775: {message_a_to_b}")
            await websocket_a.send(message_a_to_b)
            
            # 応答を待機
            try:
                response = await asyncio.wait_for(websocket_b.recv(), timeout=3.0)
                logger.info(f"8775で受信: {response}")
            except asyncio.TimeoutError:
                logger.info("8775で応答なし（正常）")
            
            await asyncio.sleep(1)
            
            # BからAへメッセージ送信
            message_b_to_a = "Message from 8775 to 8675"
            logger.info(f"8775 -> 8675: {message_b_to_a}")
            await websocket_b.send(message_b_to_a)
            
            # 応答を待機
            try:
                response = await asyncio.wait_for(websocket_a.recv(), timeout=3.0)
                logger.info(f"8675で受信: {response}")
            except asyncio.TimeoutError:
                logger.info("8675で応答なし（正常）")
            
            logger.info("双方向通信テスト完了")
            
    except Exception as e:
        logger.error(f"双方向通信テストエラー: {e}")


async def main():
    """メイン関数"""
    logger.info("WebSocketテストクライアント開始（ポート8675のみ）")
    logger.info(f"サーバー: {SERVER_HOST}")
    logger.info(f"接続ポート: {PORT_A}")
    
    try:
        # ポート8675のテストのみ実行
        await test_port_a()
        
        logger.info("テストが完了しました!")
        
    except KeyboardInterrupt:
        logger.info("テストを中断しました")
    except Exception as e:
        logger.error(f"テスト中にエラーが発生しました: {e}")


if __name__ == "__main__":
    asyncio.run(main())
