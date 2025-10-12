# WebSocket Transfer Server

ポート8675と8775で待ち受け、相互にメッセージをブロードキャスト転送するWebSocketサーバーです。

## 機能

- ポート8675と8775で同時にWebSocket接続を待ち受け
- ポート8675に送信されたメッセージをポート8775の全クライアントに転送
- ポート8775に送信されたメッセージをポート8675の全クライアントに転送
- ブロードキャスト型の転送（1対多、多対多）
- 適切なリソース管理（メモリリーク防止）
- 基本的なログ出力

## セットアップ

### 1. 仮想環境の作成と有効化

```bash
# 仮想環境を作成
python -m venv venv

# 仮想環境を有効化
# macOS/Linux:
source venv/bin/activate
# Windows:
# venv\Scripts\activate
```

### 2. 依存関係のインストール

```bash
pip install -r requirements.txt
```

## 使用方法

### サーバーの起動

```bash
python server.py
```

サーバーが起動すると以下のメッセージが表示されます：

```
WebSocket転送サーバーを起動中...
サーバー起動完了:
  ポート8675: ws://localhost:8675
  ポート8775: ws://localhost:8775
  終了するには Ctrl+C を押してください
```

### クライアントの接続

- ポート8675: `ws://<サーバーIP>:8675`
- ポート8775: `ws://<サーバーIP>:8775`

**外部接続の場合:**
- サーバーのIPアドレスを`<サーバーIP>`に置き換えてください
- 例: `ws://192.168.1.100:8675`

### 動作例

1. ポート8675にクライアントAが接続
2. ポート8775にクライアントB、Cが接続
3. クライアントAがメッセージを送信 → クライアントB、Cに転送
4. クライアントBがメッセージを送信 → クライアントAに転送

## ログ出力

サーバーは以下の情報をログ出力します：

- クライアントの接続/切断
- メッセージの受信/転送
- エラー情報
- 定期的なクリーンアップ情報

## ファイアウォール設定

外部からの接続を許可するには、以下のポートを開放してください：

### Ubuntu/Debian (ufw)
```bash
sudo ufw allow 8675
sudo ufw allow 8775
sudo ufw reload
```

### CentOS/RHEL/Fedora (firewalld)
```bash
sudo firewall-cmd --permanent --add-port=8675/tcp
sudo firewall-cmd --permanent --add-port=8775/tcp
sudo firewall-cmd --reload
```

### iptables (直接設定)
```bash
sudo iptables -A INPUT -p tcp --dport 8675 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 8775 -j ACCEPT
sudo iptables-save > /etc/iptables/rules.v4
```

## 終了方法

`Ctrl+C` を押すとサーバーが安全に終了します。

## 技術仕様

- **ライブラリ**: websockets (asyncio ベース)
- **Python**: 3.7以上
- **プロトコル**: WebSocket
- **転送方式**: ブロードキャスト
- **リソース管理**: 自動クリーンアップ（30秒間隔）
