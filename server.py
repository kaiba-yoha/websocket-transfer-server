#!/usr/bin/env python3
"""
WebSocket Transfer Server
ポート8675と8775で待ち受け、相互にメッセージをブロードキャスト転送するサーバー
"""

import asyncio
import logging
import websockets
from websockets.server import WebSocketServerProtocol
from typing import Set

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# クライアント管理用のセット
port8675_clients: Set[WebSocketServerProtocol] = set()
port8775_clients: Set[WebSocketServerProtocol] = set()


async def handle_port8675(websocket: WebSocketServerProtocol, path: str):
    """ポート8675のクライアント接続を処理"""
    client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
    logger.info(f"ポート8675にクライアント接続: {client_id}")
    
    # クライアントをセットに追加
    port8675_clients.add(websocket)
    
    try:
        async for message in websocket:
            logger.info(f"ポート8675からメッセージ受信: {message[:100]}...")
            
            # 8775の全クライアントにブロードキャスト
            if port8775_clients:
                # 切断されたクライアントを除外
                active_clients = [client for client in port8775_clients if not client.closed]
                if active_clients:
                    await websockets.broadcast(active_clients, message)
                    logger.info(f"ポート8775の{len(active_clients)}クライアントに転送完了")
                else:
                    logger.warning("ポート8775にアクティブなクライアントがありません")
            else:
                logger.warning("ポート8775にクライアントが接続されていません")
                
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"ポート8675のクライアント切断: {client_id}")
    except Exception as e:
        logger.error(f"ポート8675でエラー: {e}")
    finally:
        # クライアントをセットから削除
        port8675_clients.discard(websocket)


async def handle_port8775(websocket: WebSocketServerProtocol, path: str):
    """ポート8775のクライアント接続を処理"""
    client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
    logger.info(f"ポート8775にクライアント接続: {client_id}")
    
    # クライアントをセットに追加
    port8775_clients.add(websocket)
    
    try:
        async for message in websocket:
            logger.info(f"ポート8775からメッセージ受信: {message[:100]}...")
            
            # 8675の全クライアントにブロードキャスト
            if port8675_clients:
                # 切断されたクライアントを除外
                active_clients = [client for client in port8675_clients if not client.closed]
                if active_clients:
                    await websockets.broadcast(active_clients, message)
                    logger.info(f"ポート8675の{len(active_clients)}クライアントに転送完了")
                else:
                    logger.warning("ポート8675にアクティブなクライアントがありません")
            else:
                logger.warning("ポート8675にクライアントが接続されていません")
                
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"ポート8775のクライアント切断: {client_id}")
    except Exception as e:
        logger.error(f"ポート8775でエラー: {e}")
    finally:
        # クライアントをセットから削除
        port8775_clients.discard(websocket)


async def cleanup_clients():
    """定期的に切断されたクライアントをクリーンアップ"""
    while True:
        await asyncio.sleep(30)  # 30秒ごとにクリーンアップ
        
        # 切断されたクライアントを削除
        port8675_clients.discard(None)
        port8775_clients.discard(None)
        
        # 閉じられたクライアントを削除
        closed_8675 = {client for client in port8675_clients if client.closed}
        closed_8775 = {client for client in port8775_clients if client.closed}
        
        port8675_clients -= closed_8675
        port8775_clients -= closed_8775
        
        if closed_8675 or closed_8775:
            logger.info(f"クリーンアップ: 8675={len(closed_8675)}, 8775={len(closed_8775)}クライアント削除")


async def main():
    """メイン関数"""
    logger.info("WebSocket転送サーバーを起動中...")
    
    # 2つのサーバーを並行起動
    server_8675 = websockets.serve(handle_port8675, "localhost", 8675)
    server_8775 = websockets.serve(handle_port8775, "localhost", 8775)
    
    # クリーンアップタスクを開始
    cleanup_task = asyncio.create_task(cleanup_clients())
    
    logger.info("サーバー起動完了:")
    logger.info("  ポート8675: ws://localhost:8675")
    logger.info("  ポート8775: ws://localhost:8775")
    logger.info("  終了するには Ctrl+C を押してください")
    
    try:
        # 両方のサーバーとクリーンアップタスクを並行実行
        await asyncio.gather(
            server_8675,
            server_8775,
            cleanup_task
        )
    except KeyboardInterrupt:
        logger.info("サーバーを停止中...")
        cleanup_task.cancel()
        logger.info("サーバー停止完了")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("プログラム終了")
    except Exception as e:
        logger.error(f"予期しないエラー: {e}")
