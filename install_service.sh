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

# Python仮想環境のセットアップ
setup_venv() {
    log_step "Python仮想環境をセットアップ中..."
    
    cd $INSTALL_DIR/websocket-server
    
    # 仮想環境の作成
    sudo -u $SERVICE_USER python3 -m venv venv
    
    # 依存関係のインストール
    sudo -u $SERVICE_USER $INSTALL_DIR/websocket-server/venv/bin/pip install -r requirements.txt
    
    log_info "✓ Python仮想環境をセットアップしました"
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
    create_user
    setup_directories
    copy_files
    setup_venv
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
    log_info "=========================================="
}

# スクリプト実行
main "$@"
