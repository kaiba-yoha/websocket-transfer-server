#!/usr/bin/env python3
"""
UDP Receiver
WebSocket転送サーバーから送信されたUDPメッセージを受信・処理するプログラム
"""

import json
import logging
import socket
from typing import Dict, Any

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# UDP受信設定
UDP_HOST = "127.0.0.1"
UDP_PORT = 8080
BUFFER_SIZE = 4096


def process_received_data(data: Dict[Any, Any]) -> None:
    """受信したデータを処理"""
    logger.info(f"受信データを処理中: {data}")
    
    # ここで実際の処理を実装
    # 例: データベースへの保存、他のAPIへの転送、ログ出力など
    
    # データの種類に応じた処理
    if "timestamp" in data:
        logger.info(f"タイムスタンプ付きデータ: {data['timestamp']}")
    
    if "key" in data:
        logger.info(f"キー付きデータ: {data['key']} = {data.get('value', 'N/A')}")
    
    # カスタム処理をここに追加
    # 例: データベース保存
    # save_to_database(data)
    
    # 例: 他のAPIに転送
    # forward_to_api(data)
    
    # 例: ファイルに保存
    # save_to_file(data)
    
    logger.info("データ処理が完了しました")


def start_udp_receiver():
    """UDP受信サーバーを開始"""
    logger.info(f"UDP受信サーバーを開始: {UDP_HOST}:{UDP_PORT}")
    
    # UDPソケットを作成
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_HOST, UDP_PORT))
    
    logger.info("UDP受信サーバーが起動しました")
    logger.info("終了するには Ctrl+C を押してください")
    
    try:
        while True:
            # データを受信
            data, addr = sock.recvfrom(BUFFER_SIZE)
            logger.info(f"UDPデータを受信: {addr} -> {len(data)} bytes")
            
            try:
                # JSONデータをパース
                json_data = json.loads(data.decode('utf-8'))
                logger.info(f"JSONデータを解析: {json_data}")
                
                # データを処理
                process_received_data(json_data)
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析エラー: {e}")
                logger.error(f"受信データ: {data}")
            except UnicodeDecodeError as e:
                logger.error(f"文字エンコーディングエラー: {e}")
                logger.error(f"受信データ: {data}")
            except Exception as e:
                logger.error(f"データ処理エラー: {e}")
                
    except KeyboardInterrupt:
        logger.info("UDP受信サーバーを停止中...")
    except Exception as e:
        logger.error(f"UDP受信サーバーエラー: {e}")
    finally:
        sock.close()
        logger.info("UDP受信サーバーを停止しました")


if __name__ == "__main__":
    start_udp_receiver()
