#!/bin/bash

# WebSocket Transfer Server サービスインストールスクリプト
# Linux上でsystemdサービスとして常駐化するためのセットアップ

set -e

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ログ関数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# 設定
INSTALL_DIR="/opt/websocket-transfer-server"
SERVICE_USER="websocket"
SERVICE_GROUP="websocket"
LOG_DIR="/var/log/websocket-transfer"

# 環境変数設定
GEMINI_API_KEY=""
UDP_HOST="127.0.0.1"
UDP_PORT="8080"
UDP_RESPONSE_HOST="127.0.0.1"
UDP_RESPONSE_PORT="8081"

# 環境変数の設定
setup_environment() {
    log_step "環境変数を設定中..."
    
    # 既存の環境変数をチェック
    if [ ! -z "$GEMINI_API_KEY_ENV" ]; then
        GEMINI_API_KEY="$GEMINI_API_KEY_ENV"
        log_info "✓ 環境変数からGemini APIキーを取得しました"
    else
        # ユーザーに入力を求める
        echo ""
        log_info "Gemini APIキーの設定が必要です"
        log_info "Gemini APIキーを取得: https://makersuite.google.com/app/apikey"
        echo ""
        read -p "Gemini APIキーを入力してください: " GEMINI_API_KEY
        
        if [ -z "$GEMINI_API_KEY" ]; then
            log_warn "APIキーが入力されませんでした。後で手動で設定してください"
            GEMINI_API_KEY="your-gemini-api-key-here"
        else
            log_info "✓ Gemini APIキーを設定しました"
        fi
    fi
    
    # その他の設定を確認
    read -p "UDPホスト (デフォルト: $UDP_HOST): " input_host
    if [ ! -z "$input_host" ]; then
        UDP_HOST="$input_host"
    fi
    
    read -p "UDPポート (デフォルト: $UDP_PORT): " input_port
    if [ ! -z "$input_port" ]; then
        UDP_PORT="$input_port"
    fi
    
    read -p "UDP返信ホスト (デフォルト: $UDP_RESPONSE_HOST): " input_response_host
    if [ ! -z "$input_response_host" ]; then
        UDP_RESPONSE_HOST="$input_response_host"
    fi
    
    read -p "UDP返信ポート (デフォルト: $UDP_RESPONSE_PORT): " input_response_port
    if [ ! -z "$input_response_port" ]; then
        UDP_RESPONSE_PORT="$input_response_port"
    fi
    
    log_info "✓ 環境変数設定が完了しました"
}

# 管理者権限チェック
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "このスクリプトはroot権限で実行する必要があります"
        log_info "sudo ./install_service.sh で実行してください"
        exit 1
    fi
}

# システム要件チェック
check_requirements() {
    log_step "システム要件をチェック中..."
    
    # systemdの確認
    if ! command -v systemctl &> /dev/null; then
        log_error "systemdが利用できません。このスクリプトはsystemdベースのシステム用です。"
        exit 1
    fi
    
    # Python3の確認
    if ! command -v python3 &> /dev/null; then
        log_error "Python3がインストールされていません"
        exit 1
    fi
    
    # pipの確認
    if ! command -v pip3 &> /dev/null; then
        log_error "pip3がインストールされていません"
        exit 1
    fi
    
    log_info "✓ システム要件を満たしています"
}

# ユーザーとグループの作成
create_user() {
    log_step "サービスユーザーを作成中..."
    
    # グループの作成
    if ! getent group $SERVICE_GROUP > /dev/null 2>&1; then
        groupadd $SERVICE_GROUP
        log_info "✓ グループ '$SERVICE_GROUP' を作成しました"
    else
        log_info "✓ グループ '$SERVICE_GROUP' は既に存在します"
    fi
    
    # ユーザーの作成
    if ! getent passwd $SERVICE_USER > /dev/null 2>&1; then
        useradd -r -g $SERVICE_GROUP -s /bin/false -d $INSTALL_DIR $SERVICE_USER
        log_info "✓ ユーザー '$SERVICE_USER' を作成しました"
    else
        log_info "✓ ユーザー '$SERVICE_USER' は既に存在します"
    fi
}

# ディレクトリの作成と権限設定
setup_directories() {
    log_step "ディレクトリをセットアップ中..."
    
    # インストールディレクトリの作成
    mkdir -p $INSTALL_DIR
    log_info "✓ インストールディレクトリを作成: $INSTALL_DIR"
    
    # ログディレクトリの作成
    mkdir -p $LOG_DIR
    log_info "✓ ログディレクトリを作成: $LOG_DIR"
    
    # 権限設定
    chown -R $SERVICE_USER:$SERVICE_GROUP $INSTALL_DIR
    chown -R $SERVICE_USER:$SERVICE_GROUP $LOG_DIR
    chmod 755 $INSTALL_DIR
    chmod 755 $LOG_DIR
    
    log_info "✓ ディレクトリ権限を設定しました"
}

# ファイルのコピー
copy_files() {
    log_step "ファイルをコピー中..."
    
    # プロジェクトファイルをコピー
    cp -r websocket-server $INSTALL_DIR/
    cp -r processor $INSTALL_DIR/
    
    # 権限設定
    chown -R $SERVICE_USER:$SERVICE_GROUP $INSTALL_DIR
    find $INSTALL_DIR -type f -name "*.py" -exec chmod 644 {} \;
    find $INSTALL_DIR -type f -name "*.sh" -exec chmod 755 {} \;
    
    log_info "✓ ファイルをコピーしました"
}

# Python依存関係のインストール
install_dependencies() {
    log_step "Python依存関係をインストール中..."
    
    # システム全体に依存関係をインストール
    pip3 install -r $INSTALL_DIR/websocket-server/requirements.txt
    
    log_info "✓ Python依存関係をインストールしました"
}

# サービスファイルの更新
update_service_files() {
    log_step "サービスファイルを更新中..."
    
    # UDPレシーバーサービスの環境変数を更新
    cat > $INSTALL_DIR/processor/udp-receiver.service << EOF
[Unit]
Description=UDP Receiver for WebSocket Transfer Server
Documentation=https://github.com/your-repo/websocket-transfer-server
After=network.target
Wants=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_GROUP
WorkingDirectory=$INSTALL_DIR/processor
ExecStart=/usr/bin/python3 udp_receiver.py
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=udp-receiver

# セキュリティ設定
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$INSTALL_DIR/processor
ReadWritePaths=$LOG_DIR

# リソース制限
LimitNOFILE=65536
LimitNPROC=4096

# 環境変数
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONPATH=$INSTALL_DIR/processor
Environment=GEMINI_API_KEY=$GEMINI_API_KEY
Environment=UDP_HOST=$UDP_HOST
Environment=UDP_PORT=$UDP_PORT
Environment=UDP_RESPONSE_HOST=$UDP_RESPONSE_HOST
Environment=UDP_RESPONSE_PORT=$UDP_RESPONSE_PORT

[Install]
WantedBy=multi-user.target
EOF
    
    log_info "✓ サービスファイルを更新しました"
}

# サービスファイルのインストール
install_services() {
    log_step "systemdサービスをインストール中..."
    
    # サービスファイルをコピー
    cp $INSTALL_DIR/websocket-server/websocket-transfer.service /etc/systemd/system/
    cp $INSTALL_DIR/processor/udp-receiver.service /etc/systemd/system/
    
    # systemdの再読み込み
    systemctl daemon-reload
    
    # サービスの有効化
    systemctl enable websocket-transfer.service
    systemctl enable udp-receiver.service
    
    log_info "✓ systemdサービスをインストールしました"
}

# ログローテーションの設定
setup_logrotate() {
    log_step "ログローテーションを設定中..."
    
    cat > /etc/logrotate.d/websocket-transfer << EOF
$LOG_DIR/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $SERVICE_USER $SERVICE_GROUP
    postrotate
        systemctl reload websocket-transfer.service > /dev/null 2>&1 || true
        systemctl reload udp-receiver.service > /dev/null 2>&1 || true
    endscript
}
EOF
    
    log_info "✓ ログローテーションを設定しました"
}

# ファイアウォール設定の確認
check_firewall() {
    log_step "ファイアウォール設定を確認中..."
    
    # ufwの確認
    if command -v ufw &> /dev/null; then
        if ufw status | grep -q "Status: active"; then
            log_warn "ufwが有効です。以下のポートを開放してください:"
            log_info "  sudo ufw allow 8675"
            log_info "  sudo ufw allow 8775"
            log_info "  sudo ufw allow 8080"
            log_info "  sudo ufw allow 8081"
        fi
    fi
    
    # firewalldの確認
    if command -v firewall-cmd &> /dev/null; then
        if systemctl is-active firewalld &> /dev/null; then
            log_warn "firewalldが有効です。以下のポートを開放してください:"
            log_info "  sudo firewall-cmd --permanent --add-port=8675/tcp"
            log_info "  sudo firewall-cmd --permanent --add-port=8775/tcp"
            log_info "  sudo firewall-cmd --permanent --add-port=8080/udp"
            log_info "  sudo firewall-cmd --permanent --add-port=8081/udp"
            log_info "  sudo firewall-cmd --reload"
        fi
    fi
}

# サービスの起動
start_services() {
    log_step "サービスを起動中..."
    
    # WebSocket転送サーバーの起動
    systemctl start websocket-transfer.service
    if systemctl is-active websocket-transfer.service &> /dev/null; then
        log_info "✓ WebSocket転送サーバーが起動しました"
    else
        log_error "✗ WebSocket転送サーバーの起動に失敗しました"
        systemctl status websocket-transfer.service
        exit 1
    fi
    
    # UDP受信プログラムの起動
    systemctl start udp-receiver.service
    if systemctl is-active udp-receiver.service &> /dev/null; then
        log_info "✓ UDP受信プログラムが起動しました"
    else
        log_error "✗ UDP受信プログラムの起動に失敗しました"
        systemctl status udp-receiver.service
        exit 1
    fi
}

# メイン処理
main() {
    log_info "WebSocket Transfer Server サービスインストールを開始します"
    echo ""
    
    check_root
    check_requirements
    setup_environment
    create_user
    setup_directories
    copy_files
    install_dependencies
    update_service_files
    install_services
    setup_logrotate
    check_firewall
    start_services
    
    echo ""
    log_info "=========================================="
    log_info "インストール完了！"
    log_info "=========================================="
    log_info "WebSocket転送サーバー: ws://localhost:8675, ws://localhost:8775"
    log_info "UDP受信プログラム: 127.0.0.1:8080"
    log_info ""
    log_info "サービス管理コマンド:"
    log_info "  状態確認: sudo systemctl status websocket-transfer udp-receiver"
    log_info "  停止:     sudo systemctl stop websocket-transfer udp-receiver"
    log_info "  開始:     sudo systemctl start websocket-transfer udp-receiver"
    log_info "  再起動:   sudo systemctl restart websocket-transfer udp-receiver"
    log_info "  ログ確認: sudo journalctl -u websocket-transfer -u udp-receiver -f"
    log_info ""
    log_info "環境変数の設定:"
    log_info "  Gemini APIキー: $GEMINI_API_KEY"
    log_info "  UDPホスト: $UDP_HOST"
    log_info "  UDPポート: $UDP_PORT"
    log_info "  UDP返信ホスト: $UDP_RESPONSE_HOST"
    log_info "  UDP返信ポート: $UDP_RESPONSE_PORT"
    log_info "=========================================="
}

# スクリプト実行
main "$@"
