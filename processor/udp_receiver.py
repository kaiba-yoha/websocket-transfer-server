#!/usr/bin/env python3
"""
UDP Receiver
WebSocket転送サーバーから送信されたUDPメッセージを受信・処理するプログラム
"""

import json
import logging
import os
import socket
import time
from typing import Dict, Any, Optional
import google.generativeai as genai

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

# UDP返信設定
UDP_RESPONSE_HOST = "127.0.0.1"
UDP_RESPONSE_PORT = 8081  # WebSocketサーバーのUDP受信ポート

# Gemini API設定
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-pro')
else:
    model = None


def send_response_to_websocket(response_data: Dict[Any, Any]) -> bool:
    """WebSocketサーバーに返信を送信"""
    try:
        # JSONデータをバイト列に変換
        json_data = json.dumps(response_data).encode('utf-8')
        
        # UDPソケットを作成
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1.0)  # 1秒のタイムアウト
        
        # データを送信
        sock.sendto(json_data, (UDP_RESPONSE_HOST, UDP_RESPONSE_PORT))
        sock.close()
        
        logger.info(f"WebSocketサーバーに返信送信: {UDP_RESPONSE_HOST}:{UDP_RESPONSE_PORT}")
        return True
        
    except socket.timeout:
        logger.warning(f"WebSocket返信タイムアウト: {UDP_RESPONSE_HOST}:{UDP_RESPONSE_PORT}")
        return False
    except socket.error as e:
        logger.error(f"WebSocket返信エラー: {e}")
        return False
    except Exception as e:
        logger.error(f"WebSocket返信エラー: {e}")
        return False


def modify_text_with_ai(text: str, instruction: str = "テキストを改善してください") -> Optional[str]:
    """Gemini AIを使用してテキストを編集"""
    if not model:
        logger.error("Gemini APIキーが設定されていません")
        return None
    
    try:
        logger.info(f"Gemini AIテキスト編集を開始: {instruction}")
        
        prompt = f"""あなたはテキスト編集の専門家です。与えられた指示に従ってテキストを改善してください。

指示: {instruction}

編集するテキスト: {text}

改善されたテキスト:"""
        
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=1000,
                temperature=0.7,
            )
        )
        
        modified_text = response.text
        logger.info(f"Gemini AIテキスト編集が完了しました")
        return modified_text
        
    except Exception as e:
        logger.error(f"Gemini AIテキスト編集エラー: {e}")
        return None


def process_received_data(data: Dict[Any, Any]) -> None:
    """受信したデータを処理"""
    logger.info(f"受信データを処理中: {data}")
    
    # データの種類に応じた処理
    if "type" in data and data["type"] == "modify_text":
        logger.info("modify_textタイプのデータを処理中")
        
        # テキストと指示を取得
        text = data.get("text", "")
        instruction = data.get("instruction", "テキストを改善してください")
        
        if not text:
            logger.warning("テキストが指定されていません")
            response_data = {
                "type": "response",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "original_data": data,
                "error": "テキストが指定されていません",
                "processed": False
            }
        else:
            # AIでテキストを編集
            modified_text = modify_text_with_ai(text, instruction)
            
            if modified_text:
                response_data = {
                    "type": "response",
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "original_data": data,
                    "original_text": text,
                    "modified_text": modified_text,
                    "instruction": instruction,
                    "processed": True,
                    "message": "AIテキスト編集が完了しました"
                }
            else:
                response_data = {
                    "type": "response",
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "original_data": data,
                    "error": "AIテキスト編集に失敗しました",
                    "processed": False
                }
        
        # WebSocketサーバーに返信を送信
        success = send_response_to_websocket(response_data)
        if success:
            logger.info("WebSocketサーバーへの返信が完了しました")
        else:
            logger.warning("WebSocketサーバーへの返信に失敗しました")
        return
    
    # その他のデータタイプの処理
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
    
    # WebSocketサーバーに返信を送信
    response_data = {
        "type": "response",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "original_data": data,
        "data": "https://firebasestorage.googleapis.com/v0/b/techbias.firebasestorage.app/o/CFI_Ad-03.jpg?alt=media&token=f1a60652-069a-4985-a357-1dd28e1376cf",
        "processed": True,
        "message": "データ処理が完了しました"
    }
    
    success = send_response_to_websocket(response_data)
    if success:
        logger.info("WebSocketサーバーへの返信が完了しました")
    else:
        logger.warning("WebSocketサーバーへの返信に失敗しました")


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
