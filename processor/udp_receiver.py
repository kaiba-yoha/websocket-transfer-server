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
from PIL import Image, ImageDraw, ImageFont
import cv2
import numpy as np
import base64
import io
from google.cloud import storage as gcs
import boto3
from botocore.exceptions import ClientError
import requests
import hashlib
import shutil

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

# キャッシュ設定
CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)


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


def upload_to_gcs(image_data: bytes, bucket_name: str, blob_name: str) -> Optional[str]:
    """Google Cloud Storageに画像をアップロード"""
    try:
        logger.info(f"Google Cloud Storageにアップロード開始: {bucket_name}/{blob_name}")
        
        # GCSクライアントを初期化
        client = gcs.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        # 画像データをアップロード
        blob.upload_from_string(image_data, content_type='image/jpeg')
        
        # 公開URLを生成
        public_url = f"https://storage.googleapis.com/{bucket_name}/{blob_name}"
        
        logger.info(f"Google Cloud Storageアップロード完了: {public_url}")
        return public_url
        
    except Exception as e:
        logger.error(f"Google Cloud Storageアップロードエラー: {e}")
        return None


def upload_to_s3(image_data: bytes, bucket_name: str, key: str, region: str = "us-east-1") -> Optional[str]:
    """AWS S3に画像をアップロード"""
    try:
        logger.info(f"AWS S3にアップロード開始: {bucket_name}/{key}")
        
        # S3クライアントを初期化
        s3_client = boto3.client('s3', region_name=region)
        
        # 画像データをアップロード
        s3_client.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=image_data,
            ContentType='image/jpeg',
            ACL='public-read'  # 公開読み取り可能に設定
        )
        
        # 公開URLを生成
        public_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{key}"
        
        logger.info(f"AWS S3アップロード完了: {public_url}")
        return public_url
        
    except ClientError as e:
        logger.error(f"AWS S3アップロードエラー: {e}")
        return None
    except Exception as e:
        logger.error(f"AWS S3アップロードエラー: {e}")
        return None


def get_image_from_url(url: str) -> Optional[str]:
    """URLから画像をダウンロードしてキャッシュに保存"""
    try:
        # URLのハッシュを生成してキャッシュファイル名を作成
        url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
        cache_file_path = os.path.join(CACHE_DIR, f"{url_hash}.jpg")
        
        # キャッシュファイルが存在するかチェック
        if os.path.exists(cache_file_path):
            logger.info(f"キャッシュから画像を取得: {url}")
            return cache_file_path
        
        # 画像をダウンロード
        logger.info(f"画像をダウンロード中: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # 画像データを保存
        with open(cache_file_path, 'wb') as f:
            f.write(response.content)
        
        logger.info(f"画像をキャッシュに保存: {cache_file_path}")
        return cache_file_path
        
    except requests.exceptions.RequestException as e:
        logger.error(f"画像ダウンロードエラー: {e}")
        return None
    except Exception as e:
        logger.error(f"画像キャッシュエラー: {e}")
        return None


def trim_image_by_rect(image_path: str, rect: Dict[str, float]) -> Optional[str]:
    """画像を指定された矩形でトリミング"""
    try:
        logger.info(f"画像をトリミング中: {image_path}")
        
        # 画像を読み込み
        image = Image.open(image_path)
        img_width, img_height = image.size
        
        # 矩形の座標を計算
        center_x = rect.get('center_x', 0)
        center_y = rect.get('center_y', 0)
        width = rect.get('width', 0)
        height = rect.get('height', 0)
        
        # 矩形の境界を計算
        left = max(0, int(center_x - width / 2))
        top = max(0, int(center_y - height / 2))
        right = min(img_width, int(center_x + width / 2))
        bottom = min(img_height, int(center_y + height / 2))
        
        # トリミング実行
        trimmed_image = image.crop((left, top, right, bottom))
        
        # トリミングされた画像をBase64エンコード
        output_buffer = io.BytesIO()
        trimmed_image.save(output_buffer, format='JPEG', quality=95)
        output_buffer.seek(0)
        
        trimmed_image_base64 = base64.b64encode(output_buffer.getvalue()).decode('utf-8')
        
        logger.info("画像のトリミングが完了しました")
        return trimmed_image_base64
        
    except Exception as e:
        logger.error(f"画像トリミングエラー: {e}")
        return None


def upload_to_storage(image_data: bytes, storage_type: str = "gcs", **kwargs) -> Optional[str]:
    """ストレージに画像をアップロード（GCSまたはS3）"""
    try:
        if storage_type.lower() == "gcs":
            bucket_name = kwargs.get("bucket_name", os.getenv("GCS_BUCKET_NAME"))
            blob_name = kwargs.get("blob_name", f"composite_images/{int(time.time())}.jpg")
            return upload_to_gcs(image_data, bucket_name, blob_name)
            
        elif storage_type.lower() == "s3":
            bucket_name = kwargs.get("bucket_name", os.getenv("S3_BUCKET_NAME"))
            key = kwargs.get("key", f"composite_images/{int(time.time())}.jpg")
            region = kwargs.get("region", os.getenv("AWS_REGION", "us-east-1"))
            return upload_to_s3(image_data, bucket_name, key, region)
            
        else:
            logger.error(f"サポートされていないストレージタイプ: {storage_type}")
            return None
            
    except Exception as e:
        logger.error(f"ストレージアップロードエラー: {e}")
        return None


def create_composite_image(image_data: str, text: str, font_size: int = 40, text_color: str = "white", 
                          text_position: str = "bottom") -> Optional[str]:
    """画像とテキストを合成した画像を作成"""
    try:
        logger.info("画像とテキストの合成を開始")
        
        # Base64デコードして画像を読み込み
        if image_data.startswith('data:image'):
            # data:image/jpeg;base64, の形式の場合
            image_data = image_data.split(',')[1]
        
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))
        
        # 画像をRGBモードに変換（RGBAの場合は背景を白に）
        if image.mode == 'RGBA':
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1])
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        # テキスト描画用のImageDrawオブジェクトを作成
        draw = ImageDraw.Draw(image)
        
        # フォントの設定（システムフォントを使用）
        try:
            # 日本語フォントを試行
            font = ImageFont.truetype("/System/Library/Fonts/Hiragino Sans GB.ttc", font_size)
        except:
            try:
                # 代替フォント
                font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", font_size)
            except:
                # デフォルトフォント
                font = ImageFont.load_default()
        
        # テキストの位置を計算
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        # 画像サイズを取得
        img_width, img_height = image.size
        
        # テキストの位置を決定
        if text_position == "top":
            x = (img_width - text_width) // 2
            y = 20
        elif text_position == "center":
            x = (img_width - text_width) // 2
            y = (img_height - text_height) // 2
        elif text_position == "bottom":
            x = (img_width - text_width) // 2
            y = img_height - text_height - 20
        else:
            x = (img_width - text_width) // 2
            y = (img_height - text_height) // 2
        
        # テキストの背景を描画（可読性向上のため）
        padding = 10
        draw.rectangle([x - padding, y - padding, x + text_width + padding, y + text_height + padding], 
                      fill=(0, 0, 0, 128))
        
        # テキストを描画
        draw.text((x, y), text, fill=text_color, font=font)
        
        # 合成画像をBase64エンコード
        output_buffer = io.BytesIO()
        image.save(output_buffer, format='JPEG', quality=95)
        output_buffer.seek(0)
        
        composite_image_base64 = base64.b64encode(output_buffer.getvalue()).decode('utf-8')
        
        logger.info("画像とテキストの合成が完了しました")
        return composite_image_base64
        
    except Exception as e:
        logger.error(f"画像合成エラー: {e}")
        return None


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
    if "type" in data and data["type"] == "trimmed_img":
        logger.info("trimmed_imgタイプのデータを処理中（画像ダウンロード・トリミング）")
        
        # データから必要な情報を取得
        rect = data.get("rect", {})
        url = data.get("url", "")
        
        if not url:
            logger.warning("URLが指定されていません")
            response_data = {
                "type": "response",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "original_data": data,
                "error": "URLが指定されていません",
                "processed": False
            }
        elif not rect:
            logger.warning("矩形情報が指定されていません")
            response_data = {
                "type": "response",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "original_data": data,
                "error": "矩形情報が指定されていません",
                "processed": False
            }
        else:
            # 画像をダウンロード（キャッシュから取得または新規ダウンロード）
            image_path = get_image_from_url(url)
            
            if image_path:
                # 画像をトリミング
                trimmed_image = trim_image_by_rect(image_path, rect)
                
                if trimmed_image:
                    response_data = {
                        "type": "trimmed_img",
                        "data": trimmed_image,
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "original_data": data,
                        "rect": rect,
                        "url": url,
                        "processed": True,
                        "message": "画像のトリミングが完了しました"
                    }
                else:
                    response_data = {
                        "type": "response",
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "original_data": data,
                        "error": "画像のトリミングに失敗しました",
                        "processed": False
                    }
            else:
                response_data = {
                    "type": "response",
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "original_data": data,
                    "error": "画像のダウンロードに失敗しました",
                    "processed": False
                }
        
        # WebSocketサーバーに返信を送信
        success = send_response_to_websocket(response_data)
        if success:
            logger.info("WebSocketサーバーへの返信が完了しました")
        else:
            logger.warning("WebSocketサーバーへの返信に失敗しました")
        return
    
    elif "type" in data and data["type"] == "modified":
        logger.info("modifiedタイプのデータを処理中（画像とテキストの合成）")
        
        # 画像データとテキストを取得
        image_data = data.get("image", "")
        text = data.get("text", "")
        font_size = data.get("font_size", 40)
        text_color = data.get("text_color", "white")
        text_position = data.get("text_position", "bottom")
        
        if not image_data:
            logger.warning("画像データが指定されていません")
            response_data = {
                "type": "response",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "original_data": data,
                "error": "画像データが指定されていません",
                "processed": False
            }
        elif not text:
            logger.warning("テキストが指定されていません")
            response_data = {
                "type": "response",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "original_data": data,
                "error": "テキストが指定されていません",
                "processed": False
            }
        else:
            # 画像とテキストを合成
            composite_image = create_composite_image(
                image_data, text, font_size, text_color, text_position
            )
            
            if composite_image:
                # ストレージアップロード設定を取得
                storage_type = data.get("storage_type", os.getenv("STORAGE_TYPE", "gcs"))
                upload_to_storage_flag = data.get("upload_to_storage", True)
                
                response_data = {
                    "type": "response",
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "original_data": data,
                    "composite_image": composite_image,
                    "text": text,
                    "font_size": font_size,
                    "text_color": text_color,
                    "text_position": text_position,
                    "processed": True,
                    "message": "画像とテキストの合成が完了しました"
                }
                
                # ストレージアップロードを実行
                if upload_to_storage_flag:
                    try:
                        # Base64デコードしてバイトデータを取得
                        composite_image_bytes = base64.b64decode(composite_image)
                        
                        # ストレージアップロード設定
                        storage_kwargs = {
                            "bucket_name": data.get("bucket_name"),
                            "blob_name": data.get("blob_name", f"composite_images/{int(time.time())}.jpg"),
                            "key": data.get("key", f"composite_images/{int(time.time())}.jpg"),
                            "region": data.get("region")
                        }
                        
                        # ストレージにアップロード
                        storage_url = upload_to_storage(composite_image_bytes, storage_type, **storage_kwargs)
                        
                        if storage_url:
                            response_data["storage_url"] = storage_url
                            response_data["storage_type"] = storage_type
                            response_data["message"] = "画像とテキストの合成とストレージアップロードが完了しました"
                            logger.info(f"ストレージアップロード成功: {storage_url}")
                        else:
                            response_data["storage_error"] = "ストレージアップロードに失敗しました"
                            logger.warning("ストレージアップロードに失敗しました")
                            
                    except Exception as e:
                        response_data["storage_error"] = f"ストレージアップロードエラー: {str(e)}"
                        logger.error(f"ストレージアップロードエラー: {e}")
                
            else:
                response_data = {
                    "type": "response",
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "original_data": data,
                    "error": "画像とテキストの合成に失敗しました",
                    "processed": False
                }
        
        # WebSocketサーバーに返信を送信
        success = send_response_to_websocket(response_data)
        if success:
            logger.info("WebSocketサーバーへの返信が完了しました")
        else:
            logger.warning("WebSocketサーバーへの返信に失敗しました")
        return
    
    elif "type" in data and data["type"] == "modify_text":
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
