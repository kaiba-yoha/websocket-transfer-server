#!/usr/bin/env python3
"""
WebSocket Transfer Server
ポート8675と8775で待ち受け、相互にメッセージをブロードキャスト転送するサーバー
"""

import asyncio
import json
import logging
import socket
import websockets
from websockets.server import WebSocketServerProtocol
from typing import Set, Dict, Any

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# クライアント管理用のセット
portA_clients: Set[WebSocketServerProtocol] = set()
portB_clients: Set[WebSocketServerProtocol] = set()

# UDP送信設定
UDP_HOST = "127.0.0.1"  # ローカルUDPサーバーのアドレス
UDP_PORT = 8080  # ローカルUDPサーバーのポート


def send_to_udp(data: Dict[Any, Any]) -> bool:
    """UDPでデータを送信"""
    try:
        # JSONデータをバイト列に変換
        json_data = json.dumps(data).encode('utf-8')
        
        # UDPソケットを作成
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1.0)  # 1秒のタイムアウト
        
        # データを送信
        sock.sendto(json_data, (UDP_HOST, UDP_PORT))
        sock.close()
        
        logger.info(f"UDPにデータ送信成功: {UDP_HOST}:{UDP_PORT}")
        return True
        
    except socket.timeout:
        logger.warning(f"UDP送信タイムアウト: {UDP_HOST}:{UDP_PORT}")
        return False
    except socket.error as e:
        logger.error(f"UDP送信エラー: {e}")
        return False
    except Exception as e:
        logger.error(f"UDP送信エラー: {e}")
        return False


async def process_message(message: str) -> str:
    """メッセージを処理（JSONパース、REST API送信など）"""
    try:
        # JSONパースを試行
        data = json.loads(message)
        
        # typeパラメータをチェック
        if isinstance(data, dict) and data.get("type") == "POST":
            logger.info("UDPタイプのメッセージを検出")
            
            # dataパラメータを抽出
            udp_data = data.get("data", {})
            if udp_data:
                # UDPで送信
                success = send_to_udp(udp_data)
                if success:
                    logger.info("サーバーメッセージをUDPに転送完了")
                else:
                    logger.warning("UDPへの転送に失敗")
            else:
                logger.warning("UDPメッセージにdataパラメータがありません")
            
            # UDPメッセージは転送しない（処理済み）
            return None
        else:
            # 通常のメッセージはそのまま返す
            return message
            
    except json.JSONDecodeError:
        # JSONでない場合は通常のメッセージとして処理
        logger.debug("JSONでないメッセージを受信")
        return message
    except Exception as e:
        logger.error(f"メッセージ処理エラー: {e}")
        return message


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
            
            # メッセージを処理（JSONパース、UDP送信など）
            processed_message = process_message(message)
            
            # 処理されたメッセージがある場合のみ転送
            if processed_message is not None:
                # 8775の全クライアントにブロードキャスト
                if portB_clients:
                    # 切断されたクライアントを除外
                    active_clients = [client for client in portB_clients if not client.closed]
                    if active_clients:
                        await websockets.broadcast(active_clients, processed_message)
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
            
            # メッセージを処理（JSONパース、UDP送信など）
            processed_message = process_message(message)
            
            # 処理されたメッセージがある場合のみ転送
            if processed_message is not None:
                # 8675の全クライアントにブロードキャスト
                if portA_clients:
                    # 切断されたクライアントを除外
                    active_clients = [client for client in portA_clients if not client.closed]
                    if active_clients:
                        await websockets.broadcast(active_clients, processed_message)
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


async def main():
    """メイン関数"""
    logger.info("WebSocket転送サーバーを起動中...")
    
    # 2つのサーバーを並行起動（外部接続を許可）
    server_8675 = websockets.serve(handle_port8675, "0.0.0.0", 8675)
    server_8775 = websockets.serve(handle_port8775, "0.0.0.0", 8775)
    
    # クリーンアップタスクを開始
    cleanup_task = asyncio.create_task(cleanup_clients())
    
    logger.info("サーバー起動完了:")
    logger.info("  ポート8675: ws://0.0.0.0:8675 (外部接続可能)")
    logger.info("  ポート8775: ws://0.0.0.0:8775 (外部接続可能)")
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
