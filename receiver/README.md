# UDP Receiver

WebSocket転送サーバーから送信されたUDPメッセージを受信・処理するプログラムです。

## 機能

- UDPポート8080でメッセージを受信
- JSONデータの解析・処理
- カスタム処理ロジックの実装
- エラーハンドリングとログ出力

## 使用方法

### 起動

```bash
python udp_receiver.py
```

### 停止

`Ctrl+C` を押すとサーバーが安全に終了します。

## 設定

### UDP受信設定

```python
UDP_HOST = "127.0.0.1"  # 受信アドレス
UDP_PORT = 8080         # 受信ポート
BUFFER_SIZE = 4096      # 受信バッファサイズ
```

## カスタム処理

`process_received_data()` 関数を編集して、受信データの処理ロジックを実装してください：

```python
def process_received_data(data: Dict[Any, Any]) -> None:
    """受信したデータを処理"""
    # データベースへの保存
    # save_to_database(data)
    
    # 他のAPIへの転送
    # forward_to_api(data)
    
    # ファイルへの保存
    # save_to_file(data)
    
    # カスタム処理をここに追加
    pass
```

## ログ出力

- 受信データの詳細
- JSON解析結果
- 処理エラー
- システム状態

## 技術仕様

- **プロトコル**: UDP
- **データ形式**: JSON
- **エンコーディング**: UTF-8
- **依存関係**: 標準ライブラリのみ
