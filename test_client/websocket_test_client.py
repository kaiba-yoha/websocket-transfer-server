#!/usr/bin/env python3
"""
WebSocket Transfer Server テストクライアント
ポート8675と8775に接続してメッセージの送受信をテストする
"""

import asyncio
import json
import logging
import websockets
from websockets.client import WebSocketClientProtocol
from typing import Optional
import time

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# サーバー設定
SERVER_HOST = "35.202.19.18"
PORT_A = 8675
PORT_B = 8775


class WebSocketTestClient:
    """WebSocketテストクライアント"""
    
    def __init__(self, port: int, client_name: str = "TestClient"):
        self.port = port
        self.client_name = client_name
        self.websocket: Optional[WebSocketClientProtocol] = None
        self.connected = False
        
    async def connect(self) -> bool:
        """WebSocketサーバーに接続"""
        try:
            uri = f"ws://{SERVER_HOST}:{self.port}"
            logger.info(f"{self.client_name}: {uri}に接続中...")
            
            self.websocket = await websockets.connect(uri)
            self.connected = True
            logger.info(f"{self.client_name}: 接続成功!")
            return True
            
        except Exception as e:
            logger.error(f"{self.client_name}: 接続失敗 - {e}")
            return False
    
    async def disconnect(self):
        """WebSocket接続を切断"""
        if self.websocket and self.connected:
            await self.websocket.close()
            self.connected = False
            logger.info(f"{self.client_name}: 接続を切断しました")
    
    async def send_message(self, message: str) -> bool:
        """メッセージを送信"""
        if not self.connected or not self.websocket:
            logger.error(f"{self.client_name}: 接続されていません")
            return False
            
        try:
            await self.websocket.send(message)
            logger.info(f"{self.client_name}: メッセージ送信 - {message[:50]}...")
            return True
        except Exception as e:
            logger.error(f"{self.client_name}: メッセージ送信失敗 - {e}")
            return False
    
    async def send_json_message(self, data: dict) -> bool:
        """JSONメッセージを送信"""
        try:
            json_message = json.dumps(data, ensure_ascii=False)
            return await self.send_message(json_message)
        except Exception as e:
            logger.error(f"{self.client_name}: JSONメッセージ送信失敗 - {e}")
            return False
    
    async def listen_for_messages(self, duration: int = 10):
        """指定時間メッセージを受信"""
        if not self.connected or not self.websocket:
            logger.error(f"{self.client_name}: 接続されていません")
            return
            
        logger.info(f"{self.client_name}: {duration}秒間メッセージを受信待機中...")
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration:
                try:
                    # タイムアウト付きでメッセージを受信
                    message = await asyncio.wait_for(
                        self.websocket.recv(), 
                        timeout=1.0
                    )
                    logger.info(f"{self.client_name}: メッセージ受信 - {message[:100]}...")
                    
                    # JSONメッセージの場合は解析して表示
                    try:
                        json_data = json.loads(message)
                        logger.info(f"{self.client_name}: JSONデータ - {json_data}")
                    except json.JSONDecodeError:
                        pass  # 通常のテキストメッセージ
                        
                except asyncio.TimeoutError:
                    # タイムアウトは正常（継続ループ）
                    continue
                except websockets.exceptions.ConnectionClosed:
                    logger.info(f"{self.client_name}: サーバーから切断されました")
                    break
                except Exception as e:
                    logger.error(f"{self.client_name}: メッセージ受信エラー - {e}")
                    break
                    
        except Exception as e:
            logger.error(f"{self.client_name}: リスナーエラー - {e}")


async def test_basic_connection():
    """基本的な接続テスト（ポート8675のみ）"""
    logger.info("=== 基本的な接続テスト開始（ポート8675のみ） ===")
    
    # ポート8675に接続
    client_a = WebSocketTestClient(PORT_A, "Client-A")
    success_a = await client_a.connect()
    
    if not success_a:
        logger.error("ポート8675への接続に失敗しました")
        return False
    
    # 接続成功
    logger.info("ポート8675への接続が成功しました")
    
    # クリーンアップ
    await client_a.disconnect()
    
    logger.info("=== 基本的な接続テスト完了 ===")
    return True


async def test_message_sending():
    """メッセージ送信テスト（ポート8675のみ）"""
    logger.info("=== メッセージ送信テスト開始（ポート8675のみ） ===")
    
    # ポート8675に接続
    client_a = WebSocketTestClient(PORT_A, "Client-A")
    if not await client_a.connect():
        logger.error("ポート8675への接続に失敗しました")
        return False
    
    # メッセージリスナーを開始
    listen_task_a = asyncio.create_task(client_a.listen_for_messages(10))
    
    # 少し待機してからメッセージを送信
    await asyncio.sleep(1)
    
    # テストメッセージを送信
    test_messages = [
        "Hello from Client-A!",
        "Test message 1",
        "Test message 2",
        json.dumps({"type": "printURL", "data": "https://firebasestorage.googleapis.com/v0/b/techbias.firebasestorage.app/o/AD-1.jpg?alt=media&token=968c4fae-6b62-460e-b6e2-84809206bc91", "timestamp": time.time()})
    ]
    
    for i, message in enumerate(test_messages):
        logger.info(f"メッセージ {i+1} を送信中...")
        await client_a.send_message(message)
        await asyncio.sleep(2)  # 2秒間隔で送信
    
    # リスナータスクの完了を待機
    await listen_task_a
    
    # クリーンアップ
    await client_a.disconnect()
    
    logger.info("=== メッセージ送信テスト完了 ===")
    return True


async def test_udp_message():
    """UDPメッセージテスト（type: POST）- ポート8675のみ"""
    logger.info("=== UDPメッセージテスト開始（ポート8675のみ） ===")
    
    # ポート8675に接続
    client_a = WebSocketTestClient(PORT_A, "Client-A")
    if not await client_a.connect():
        logger.error("ポート8675への接続に失敗しました")
        return False
    
    # メッセージリスナーを開始
    listen_task_a = asyncio.create_task(client_a.listen_for_messages(10))
    
    await asyncio.sleep(1)
    
    # UDPタイプのメッセージを送信
    udp_message = {
        "type": "printURL",
        "data": "https://firebasestorage.googleapis.com/v0/b/techbias.firebasestorage.app/o/AD-1.jpg?alt=media&token=968c4fae-6b62-460e-b6e2-84809206bc91"
    }
    
    logger.info("UDPタイプのメッセージを送信中...")
    await client_a.send_json_message(udp_message)
    
    # リスナータスクの完了を待機
    await listen_task_a
    
    # クリーンアップ
    await client_a.disconnect()
    
    logger.info("=== UDPメッセージテスト完了 ===")
    return True


async def main():
    """メイン関数"""
    logger.info("WebSocket Transfer Server テストクライアントを開始します（ポート8675のみ）")
    logger.info(f"サーバー: {SERVER_HOST}")
    logger.info(f"接続ポート: {PORT_A}")
    
    try:
        # 基本的な接続テスト
        if not await test_basic_connection():
            logger.error("基本的な接続テストに失敗しました")
            return
        
        await asyncio.sleep(2)
        
        # メッセージ送信テスト
        if not await test_message_sending():
            logger.error("メッセージ送信テストに失敗しました")
            return
        
        await asyncio.sleep(2)
        
        # UDPメッセージテスト
        if not await test_udp_message():
            logger.error("UDPメッセージテストに失敗しました")
            return
        
        logger.info("すべてのテストが完了しました!")
        
    except KeyboardInterrupt:
        logger.info("テストを中断しました")
    except Exception as e:
        logger.error(f"テスト中にエラーが発生しました: {e}")


if __name__ == "__main__":
    asyncio.run(main())
