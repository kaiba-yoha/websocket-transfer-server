#!/usr/bin/env python3
"""
WebSocket Transfer Server
ポート8675と8775で待ち受け、相互にメッセージをブロードキャスト転送するサーバー
WSS（WebSocket Secure）対応
"""

import asyncio
import logging
import ssl
import websockets
from websockets.server import WebSocketServerProtocol
from typing import Set, Optional

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# クライアント管理用のセット
portA_clients: Set[WebSocketServerProtocol] = set()
portB_clients: Set[WebSocketServerProtocol] = set()


async def handle_port8675(websocket: WebSocketServerProtocol, path: str):
    """ポート8675のクライアント接続を処理"""
    global portA_clients, portB_clients
    
    client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
    logger.info(f"ポート8675にクライアント接続: {client_id}")
    
    # クライアントをセットに追加
    portA_clients.add(websocket)
    
    try:
        async for message in websocket:
            logger.info(f"ポート8675からメッセージ受信: {message[:100]}...")
            
            # 8775の全クライアントにブロードキャスト
            if portB_clients:
                # 切断されたクライアントを除外
                active_clients = [client for client in portB_clients if not client.closed]
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
        portA_clients.discard(websocket)


async def handle_port8775(websocket: WebSocketServerProtocol, path: str):
    """ポート8775のクライアント接続を処理"""
    global portA_clients, portB_clients
    
    client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
    logger.info(f"ポート8775にクライアント接続: {client_id}")
    
    # クライアントをセットに追加
    portB_clients.add(websocket)
    
    try:
        async for message in websocket:
            logger.info(f"ポート8775からメッセージ受信: {message[:100]}...")
            
            # 8675の全クライアントにブロードキャスト
            if portA_clients:
                # 切断されたクライアントを除外
                active_clients = [client for client in portA_clients if not client.closed]
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
        portB_clients.discard(websocket)


async def cleanup_clients():
    """定期的に切断されたクライアントをクリーンアップ"""
    global portA_clients, portB_clients
    
    while True:
        await asyncio.sleep(30)  # 30秒ごとにクリーンアップ
        
        # 切断されたクライアントを削除
        portA_clients.discard(None)
        portB_clients.discard(None)
        
        # 閉じられたクライアントを削除
        closed_A = {client for client in portA_clients if client.closed}
        closed_B = {client for client in portB_clients if client.closed}
        
        portA_clients -= closed_A
        portB_clients -= closed_B
        
        if closed_A or closed_B:
            logger.info(f"クリーンアップ: 8675={len(closed_A)}, 8775={len(closed_B)}クライアント削除")


def create_ssl_context(cert_file: Optional[str] = None, key_file: Optional[str] = None) -> Optional[ssl.SSLContext]:
    """SSLコンテキストを作成"""
    if not cert_file or not key_file:
        logger.warning("SSL証明書が指定されていません。HTTP接続のみ利用可能です。")
        return None
    
    try:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(cert_file, key_file)
        logger.info(f"SSL証明書を読み込みました: {cert_file}")
        return ssl_context
    except Exception as e:
        logger.error(f"SSL証明書の読み込みに失敗: {e}")
        return None


async def main():
    """メイン関数"""
    import argparse
    
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(description='WebSocket Transfer Server')
    parser.add_argument('--cert', help='SSL証明書ファイル (.crt)')
    parser.add_argument('--key', help='SSL秘密鍵ファイル (.key)')
    parser.add_argument('--port-a', type=int, default=8675, help='ポートA (デフォルト: 8675)')
    parser.add_argument('--port-b', type=int, default=8775, help='ポートB (デフォルト: 8775)')
    args = parser.parse_args()
    
    logger.info("WebSocket転送サーバーを起動中...")
    
    # SSLコンテキストの作成
    ssl_context = create_ssl_context(args.cert, args.key)
    
    # 2つのサーバーを並行起動（外部接続を許可）
    server_8675 = websockets.serve(handle_port8675, "0.0.0.0", args.port_a, ssl=ssl_context)
    server_8775 = websockets.serve(handle_port8775, "0.0.0.0", args.port_b, ssl=ssl_context)
    
    # クリーンアップタスクを開始
    cleanup_task = asyncio.create_task(cleanup_clients())
    
    # プロトコルを決定
    protocol = "wss" if ssl_context else "ws"
    
    logger.info("サーバー起動完了:")
    logger.info(f"  ポート{args.port_a}: {protocol}://0.0.0.0:{args.port_a} (外部接続可能)")
    logger.info(f"  ポート{args.port_b}: {protocol}://0.0.0.0:{args.port_b} (外部接続可能)")
    if ssl_context:
        logger.info("  SSL/TLS暗号化が有効です")
    else:
        logger.info("  SSL/TLS暗号化は無効です（HTTP接続のみ）")
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
