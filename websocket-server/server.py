#!/usr/bin/env python3
"""
WebSocket Transfer Server
ポート8675と8775で待ち受け、相互にメッセージをブロードキャスト転送するサーバー
"""

import asyncio
import json
import logging
import socket
import threading
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

# UDP受信設定（返信用）
UDP_RECEIVE_HOST = "127.0.0.1"
UDP_RECEIVE_PORT = 8081  # WebSocketサーバーがUDPを受信するポート


def is_websocket_open(connection: Any) -> bool:
    """websockets のバージョン差異を吸収して接続が開いているか判定する。

    優先順:
      - connection.closed が bool ならその否定
      - connection.open が bool ならその値
      - connection.state の name が OPEN なら True
      - 上記が取得できなければ True を返して楽観的に扱う
    """
    try:
        closed_attr = getattr(connection, "closed", None)
        if isinstance(closed_attr, bool):
            return not closed_attr

        open_attr = getattr(connection, "open", None)
        if isinstance(open_attr, bool):
            return open_attr

        state_attr = getattr(connection, "state", None)
        if state_attr is not None:
            state_name = getattr(state_attr, "name", None)
            if isinstance(state_name, str):
                return state_name.upper() == "OPEN"
    except Exception:
        pass
    return True


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


def start_udp_receiver():
    """UDP受信サーバーを開始（返信用）"""
    logger.info(f"UDP受信サーバーを開始: {UDP_RECEIVE_HOST}:{UDP_RECEIVE_PORT}")
    
    # メインスレッドのイベントループを取得
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # イベントループが存在しない場合は新しく作成
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # UDPソケットを作成
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_RECEIVE_HOST, UDP_RECEIVE_PORT))
    sock.settimeout(1.0)  # 1秒のタイムアウト
    
    try:
        while True:
            try:
                # データを受信
                data, addr = sock.recvfrom(4096)
                logger.info(f"UDP返信データを受信: {addr} -> {len(data)} bytes")
                
                try:
                    # JSONデータをパース
                    json_data = json.loads(data.decode('utf-8'))
                    logger.info(f"UDP返信JSONデータ: {json_data}")
                    
                    # WebSocketクライアントにブロードキャスト
                    asyncio.run_coroutine_threadsafe(
                        broadcast_to_all_clients(json_data),
                        loop
                    )
                    
                except json.JSONDecodeError as e:
                    logger.error(f"UDP返信JSON解析エラー: {e}")
                except UnicodeDecodeError as e:
                    logger.error(f"UDP返信文字エンコーディングエラー: {e}")
                except Exception as e:
                    logger.error(f"UDP返信処理エラー: {e}")
                    
            except socket.timeout:
                # タイムアウトは正常（継続ループ）
                continue
            except Exception as e:
                logger.error(f"UDP受信エラー: {e}")
                break
                
    except KeyboardInterrupt:
        logger.info("UDP受信サーバーを停止中...")
    except Exception as e:
        logger.error(f"UDP受信サーバーエラー: {e}")
    finally:
        sock.close()
        logger.info("UDP受信サーバーを停止しました")


async def broadcast_to_all_clients(data: Dict[Any, Any]) -> None:
    """全クライアントにブロードキャスト"""
    global portA_clients, portB_clients
    
    # データをJSON文字列に変換
    message = json.dumps(data)
    
    # ポートAのクライアントにブロードキャスト
    if portA_clients:
        active_clients_A = [client for client in portA_clients if is_websocket_open(client)]
        if active_clients_A:
            websockets.broadcast(active_clients_A, message)
            logger.info(f"ポートAの{len(active_clients_A)}クライアントにUDP返信をブロードキャスト")
    
    # ポートBのクライアントにブロードキャスト
    if portB_clients:
        active_clients_B = [client for client in portB_clients if is_websocket_open(client)]
        if active_clients_B:
            websockets.broadcast(active_clients_B, message)
            logger.info(f"ポートBの{len(active_clients_B)}クライアントにUDP返信をブロードキャスト")


async def process_message(message: str) -> str | None:
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
                logger.info(f"サーバーメッセージをUDPに転送: {udp_data}")
                # UDPで送信
                try:
                    success = send_to_udp(udp_data)
                    if success:
                        logger.info("サーバーメッセージをUDPに転送完了")
                    else:
                        logger.warning("UDPへの転送に失敗")
                except Exception as udp_error:
                    logger.error(f"UDP送信エラー: {udp_error}")
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
        logger.error(f"エラー詳細: {type(e).__name__}: {str(e)}")
        return message


async def handle_port8675(websocket: WebSocketServerProtocol, *args):
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
            try:
                processed_message = await process_message(message)
            except Exception as e:
                logger.error(f"process_message処理エラー: {e}")
                logger.error(f"メッセージ内容: {message[:100]}...")
                continue
            
            # 処理されたメッセージがある場合のみ転送
            if processed_message is not None:
                # 8775の全クライアントにブロードキャスト
                if portB_clients:
                    # 切断されたクライアントを除外
                    active_clients = [client for client in portB_clients if is_websocket_open(client)]
                    if active_clients:
                        websockets.broadcast(active_clients, processed_message)
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


async def handle_port8775(websocket: WebSocketServerProtocol, *args):
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
            try:
                processed_message = await process_message(message)
            except Exception as e:
                logger.error(f"process_message処理エラー: {e}")
                logger.error(f"メッセージ内容: {message[:100]}...")
                continue
            
            # 処理されたメッセージがある場合のみ転送
            if processed_message is not None:
                # 8675の全クライアントにブロードキャスト
                if portA_clients:
                    # 切断されたクライアントを除外
                    active_clients = [client for client in portA_clients if is_websocket_open(client)]
                    if active_clients:
                        websockets.broadcast(active_clients, processed_message)
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
        closed_A = {client for client in portA_clients if not is_websocket_open(client)}
        closed_B = {client for client in portB_clients if not is_websocket_open(client)}
        
        portA_clients -= closed_A
        portB_clients -= closed_B
        
        if closed_A or closed_B:
            logger.info(f"クリーンアップ: 8675={len(closed_A)}, 8775={len(closed_B)}クライアント削除")


async def main():
    """メイン関数"""
    logger.info("WebSocket転送サーバーを起動中...")
    
    # UDP受信サーバーを別スレッドで開始
    udp_thread = threading.Thread(target=start_udp_receiver, daemon=True)
    udp_thread.start()
    logger.info("UDP受信サーバーを別スレッドで開始しました")
    
    # クリーンアップタスクを開始
    cleanup_task = asyncio.create_task(cleanup_clients())
    
    logger.info("サーバー起動完了:")
    logger.info("  ポート8675: ws://0.0.0.0:8675 (外部接続可能)")
    logger.info("  ポート8775: ws://0.0.0.0:8775 (外部接続可能)")
    logger.info("  UDP受信: 127.0.0.1:8081 (返信用)")
    logger.info("  終了するには Ctrl+C を押してください")
    
    try:
        # websockets 10.x では、serve()はコンテキストマネージャーとして使用
        async with websockets.serve(handle_port8675, "0.0.0.0", 8675), \
                   websockets.serve(handle_port8775, "0.0.0.0", 8775):
            # サーバーが起動したら、無限待機
            await cleanup_task
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
