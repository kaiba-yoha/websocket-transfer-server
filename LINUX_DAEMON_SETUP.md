# WebSocket Transfer Server Linux常駐化手順書

このドキュメントでは、WebSocket Transfer ServerをLinux上でsystemdサービスとして常駐化する手順を説明します。

## 概要

- **WebSocket転送サーバー**: ポート8675と8775でWebSocket接続を受け付け、相互にメッセージを転送
- **UDP受信プログラム**: ポート8080でUDPデータを受信し、WebSocketクライアントにブロードキャスト
- **systemdサービス**: 自動起動、自動再起動、ログ管理機能付き

## システム要件

- Linux OS (systemd対応)
- Python 3.6以上
- pip3
- root権限
- システム全体にPython依存関係をインストール可能

## インストール手順

### 1. 自動インストール（推奨）

```bash
# プロジェクトディレクトリに移動
cd /path/to/websocket-transfer-server

# インストールスクリプトを実行
sudo ./install_service.sh
```

### 2. 手動インストール

#### 2.1 サービスユーザーの作成

```bash
# グループとユーザーを作成
sudo groupadd websocket
sudo useradd -r -g websocket -s /bin/false -d /opt/websocket-transfer-server websocket
```

#### 2.2 ディレクトリの作成

```bash
# インストールディレクトリ
sudo mkdir -p /opt/websocket-transfer-server
sudo mkdir -p /var/log/websocket-transfer

# 権限設定
sudo chown -R websocket:websocket /opt/websocket-transfer-server
sudo chown -R websocket:websocket /var/log/websocket-transfer
```

#### 2.3 ファイルのコピー

```bash
# プロジェクトファイルをコピー
sudo cp -r websocket-server /opt/websocket-transfer-server/
sudo cp -r processor /opt/websocket-transfer-server/

# 権限設定
sudo chown -R websocket:websocket /opt/websocket-transfer-server
```

#### 2.4 Python依存関係のインストール

```bash
# システム全体に依存関係をインストール
sudo pip3 install -r /opt/websocket-transfer-server/websocket-server/requirements.txt
```

#### 2.5 systemdサービスのインストール

```bash
# サービスファイルをコピー
sudo cp websocket-server/websocket-transfer.service /etc/systemd/system/
sudo cp processor/udp-receiver.service /etc/systemd/system/

# systemdの再読み込み
sudo systemctl daemon-reload

# サービスの有効化
sudo systemctl enable websocket-transfer.service
sudo systemctl enable udp-receiver.service
```

#### 2.6 ログローテーションの設定

```bash
# ログローテーション設定をコピー
sudo cp logrotate.conf /etc/logrotate.d/websocket-transfer
```

## サービス管理

### 基本操作

```bash
# サービス管理スクリプトを使用（推奨）
./manage_service.sh start    # 開始
./manage_service.sh stop     # 停止
./manage_service.sh restart  # 再起動
./manage_service.sh status   # 状態確認
./manage_service.sh logs     # ログ表示
```

### systemctlコマンド直接使用

```bash
# サービス開始
sudo systemctl start websocket-transfer.service
sudo systemctl start udp-receiver.service

# サービス停止
sudo systemctl stop websocket-transfer.service
sudo systemctl stop udp-receiver.service

# サービス再起動
sudo systemctl restart websocket-transfer.service
sudo systemctl restart udp-receiver.service

# 状態確認
sudo systemctl status websocket-transfer.service
sudo systemctl status udp-receiver.service

# 自動起動の有効化/無効化
sudo systemctl enable websocket-transfer.service
sudo systemctl disable websocket-transfer.service
```

### ログの確認

```bash
# リアルタイムログ表示
sudo journalctl -u websocket-transfer -u udp-receiver -f

# 特定のサービスのログ
sudo journalctl -u websocket-transfer -f

# 過去のログ
sudo journalctl -u websocket-transfer --since "1 hour ago"
```

## 設定ファイル

### WebSocket転送サーバー設定

- **ファイル**: `/opt/websocket-transfer-server/websocket-server/server.py`
- **ポート**: 8675, 8775
- **UDP送信先**: 127.0.0.1:8080
- **UDP受信**: 127.0.0.1:8081

### UDP受信プログラム設定

- **ファイル**: `/opt/websocket-transfer-server/processor/udp_receiver.py`
- **UDP受信**: 127.0.0.1:8080

## ファイアウォール設定

### ufwを使用する場合

```bash
sudo ufw allow 8675
sudo ufw allow 8775
sudo ufw allow 8080/udp
sudo ufw allow 8081/udp
```

### firewalldを使用する場合

```bash
sudo firewall-cmd --permanent --add-port=8675/tcp
sudo firewall-cmd --permanent --add-port=8775/tcp
sudo firewall-cmd --permanent --add-port=8080/udp
sudo firewall-cmd --permanent --add-port=8081/udp
sudo firewall-cmd --reload
```

## トラブルシューティング

### サービスが起動しない場合

1. **ログの確認**
   ```bash
   sudo journalctl -u websocket-transfer -u udp-receiver --no-pager
   ```

2. **依存関係の確認**
   ```bash
   # Pythonの確認
   python3 --version
   
   # 依存関係の確認
   pip3 list
   ```

3. **権限の確認**
   ```bash
   ls -la /opt/websocket-transfer-server/
   ls -la /var/log/websocket-transfer/
   ```

### ポートが使用できない場合

```bash
# ポート使用状況の確認
sudo netstat -tlnp | grep -E ":(8675|8775|8080|8081)"
sudo ss -tlnp | grep -E ":(8675|8775|8080|8081)"

# プロセスの確認
sudo ps aux | grep -E "(websocket|udp_receiver)"
```

### ログファイルの確認

```bash
# アプリケーションログ
sudo tail -f /var/log/websocket-transfer/*.log

# systemdログ
sudo journalctl -u websocket-transfer -u udp-receiver --since "1 hour ago"
```

## アンインストール

### 自動アンインストール

```bash
./manage_service.sh uninstall
```

### 手動アンインストール

```bash
# サービス停止
sudo systemctl stop websocket-transfer.service udp-receiver.service

# サービス無効化
sudo systemctl disable websocket-transfer.service udp-receiver.service

# サービスファイル削除
sudo rm -f /etc/systemd/system/websocket-transfer.service
sudo rm -f /etc/systemd/system/udp-receiver.service

# systemd再読み込み
sudo systemctl daemon-reload

# ログローテーション設定削除
sudo rm -f /etc/logrotate.d/websocket-transfer

# ファイル削除（オプション）
sudo rm -rf /opt/websocket-transfer-server
sudo rm -rf /var/log/websocket-transfer

# ユーザー削除（オプション）
sudo userdel websocket
sudo groupdel websocket
```

## 監視とメンテナンス

### ヘルスチェック

```bash
# サービス状態の確認
./manage_service.sh status

# ポート接続テスト
telnet localhost 8675
telnet localhost 8775
```

### ログローテーション

- ログは自動的に日次でローテーションされます
- 30日分のログが保持されます
- 古いログは自動的に圧縮されます

### パフォーマンス監視

```bash
# リソース使用状況
sudo systemctl status websocket-transfer.service udp-receiver.service

# メモリ使用量
ps aux | grep -E "(websocket|udp_receiver)"

# ネットワーク接続数
sudo netstat -an | grep -E ":(8675|8775)" | wc -l
```

## セキュリティ考慮事項

- サービスは専用ユーザー（websocket）で実行されます
- 最小権限の原則に従って設定されています
- ログファイルの権限は適切に設定されています
- ファイアウォール設定を確認してください

## サポート

問題が発生した場合は、以下の情報を収集してください：

1. システム情報: `uname -a`
2. サービス状態: `sudo systemctl status websocket-transfer udp-receiver`
3. ログ: `sudo journalctl -u websocket-transfer -u udp-receiver --no-pager`
4. ポート使用状況: `sudo netstat -tlnp | grep -E ":(8675|8775|8080|8081)"`
