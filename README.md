# WebSocket Transfer Server

WebSocket転送サーバーとUDP受信プログラムの統合システムです。

## プロジェクト構造

```
websocket-transfer-server/
├── server/                 # WebSocket転送サーバー
│   ├── server.py          # メインサーバー
│   ├── requirements.txt   # 依存関係
│   ├── setup.sh          # セットアップスクリプト
│   └── README.md         # サーバー説明
├── receiver/              # UDP受信プログラム
│   ├── udp_receiver.py   # UDP受信サーバー
│   ├── requirements.txt   # 依存関係
│   └── README.md         # 受信プログラム説明
└── README.md             # このファイル
```

## システム概要

### 1. WebSocket転送サーバー (`server/`)
- ポート8675と8775でWebSocket接続を待ち受け
- クライアント間でメッセージをブロードキャスト転送
- JSONメッセージの`type: "POST"`を検出してUDP送信

### 2. UDP受信プログラム (`receiver/`)
- ポート8080でUDPメッセージを受信
- JSONデータを解析・処理
- カスタム処理ロジックを実装可能

## 使用方法

### 1. WebSocket転送サーバーの起動

```bash
cd server
./setup.sh  # 初回のみ
python server.py
```

### 2. UDP受信プログラムの起動

```bash
cd receiver
python udp_receiver.py
```

### 3. クライアント接続

- **ポート8675**: `ws://localhost:8675`
- **ポート8775**: `ws://localhost:8775`

## メッセージ形式

### UDP送信用メッセージ
```json
{
  "type": "POST",
  "data": {
    "key": "value",
    "timestamp": "2025-01-01T00:00:00Z"
  }
}
```

### 通常転送メッセージ
```json
{
  "message": "Hello World",
  "user": "client1"
}
```

## 動作フロー

1. **WebSocketクライアント** → WebSocket転送サーバー
2. **JSON解析** → `type: "POST"`を検出
3. **UDP送信** → `127.0.0.1:8080`
4. **UDP受信** → 受信プログラムで処理
5. **通常メッセージ** → 他のWebSocketクライアントに転送

## 設定

### WebSocket転送サーバー
- **ポート**: 8675, 8775
- **UDP送信先**: `127.0.0.1:8080`

### UDP受信プログラム
- **受信ポート**: 8080
- **バッファサイズ**: 4096 bytes

## 開発・カスタマイズ

### UDP受信プログラムのカスタマイズ

`receiver/udp_receiver.py`の`process_received_data()`関数を編集：

```python
def process_received_data(data: Dict[Any, Any]) -> None:
    # データベース保存
    # save_to_database(data)
    
    # 他のAPIに転送
    # forward_to_api(data)
    
    # ファイル保存
    # save_to_file(data)
    
    # カスタム処理
    pass
```

## 技術仕様

- **WebSocket**: websockets (asyncio ベース)
- **UDP**: 標準socketライブラリ
- **データ形式**: JSON
- **Python**: 3.7以上