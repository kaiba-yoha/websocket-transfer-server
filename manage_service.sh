#!/bin/bash

# WebSocket Transfer Server サービス管理スクリプト
# インストール済みサービスの管理用

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

# サービス名
WEBSOCKET_SERVICE="websocket-transfer.service"
UDP_SERVICE="udp-receiver.service"

# 使用方法の表示
show_usage() {
    echo "WebSocket Transfer Server サービス管理スクリプト"
    echo ""
    echo "使用方法:"
    echo "  $0 {start|stop|restart|status|logs|enable|disable|uninstall}"
    echo ""
    echo "コマンド:"
    echo "  start     - サービスを開始"
    echo "  stop      - サービスを停止"
    echo "  restart   - サービスを再起動"
    echo "  status    - サービス状態を表示"
    echo "  logs      - ログを表示（リアルタイム）"
    echo "  enable    - サービスを自動起動に設定"
    echo "  disable   - サービス自動起動を無効化"
    echo "  uninstall - サービスをアンインストール"
    echo ""
}

# サービス状態の確認
check_services() {
    local websocket_status=$(systemctl is-active $WEBSOCKET_SERVICE 2>/dev/null || echo "inactive")
    local udp_status=$(systemctl is-active $UDP_SERVICE 2>/dev/null || echo "inactive")
    
    echo "サービス状態:"
    echo "  WebSocket転送サーバー: $websocket_status"
    echo "  UDP受信プログラム:    $udp_status"
    echo ""
}

# サービス開始
start_services() {
    log_step "サービスを開始中..."
    
    systemctl start $WEBSOCKET_SERVICE
    if systemctl is-active $WEBSOCKET_SERVICE &> /dev/null; then
        log_info "✓ WebSocket転送サーバーが開始されました"
    else
        log_error "✗ WebSocket転送サーバーの開始に失敗しました"
        return 1
    fi
    
    systemctl start $UDP_SERVICE
    if systemctl is-active $UDP_SERVICE &> /dev/null; then
        log_info "✓ UDP受信プログラムが開始されました"
    else
        log_error "✗ UDP受信プログラムの開始に失敗しました"
        return 1
    fi
    
    check_services
}

# サービス停止
stop_services() {
    log_step "サービスを停止中..."
    
    systemctl stop $WEBSOCKET_SERVICE
    log_info "✓ WebSocket転送サーバーを停止しました"
    
    systemctl stop $UDP_SERVICE
    log_info "✓ UDP受信プログラムを停止しました"
    
    check_services
}

# サービス再起動
restart_services() {
    log_step "サービスを再起動中..."
    
    systemctl restart $WEBSOCKET_SERVICE
    if systemctl is-active $WEBSOCKET_SERVICE &> /dev/null; then
        log_info "✓ WebSocket転送サーバーを再起動しました"
    else
        log_error "✗ WebSocket転送サーバーの再起動に失敗しました"
        return 1
    fi
    
    systemctl restart $UDP_SERVICE
    if systemctl is-active $UDP_SERVICE &> /dev/null; then
        log_info "✓ UDP受信プログラムを再起動しました"
    else
        log_error "✗ UDP受信プログラムの再起動に失敗しました"
        return 1
    fi
    
    check_services
}

# サービス状態表示
show_status() {
    log_step "サービス状態を確認中..."
    
    echo "詳細状態:"
    systemctl status $WEBSOCKET_SERVICE $UDP_SERVICE --no-pager
    echo ""
    
    check_services
    
    # ポート使用状況の確認
    echo "ポート使用状況:"
    if command -v netstat &> /dev/null; then
        netstat -tlnp | grep -E ":(8675|8775|8080|8081)" || echo "  該当するポートが見つかりません"
    elif command -v ss &> /dev/null; then
        ss -tlnp | grep -E ":(8675|8775|8080|8081)" || echo "  該当するポートが見つかりません"
    fi
    echo ""
}

# ログ表示
show_logs() {
    log_step "ログを表示中... (Ctrl+Cで終了)"
    echo ""
    
    # リアルタイムログ表示
    journalctl -u $WEBSOCKET_SERVICE -u $UDP_SERVICE -f --no-pager
}

# サービス有効化
enable_services() {
    log_step "サービス自動起動を有効化中..."
    
    systemctl enable $WEBSOCKET_SERVICE
    log_info "✓ WebSocket転送サーバーの自動起動を有効化しました"
    
    systemctl enable $UDP_SERVICE
    log_info "✓ UDP受信プログラムの自動起動を有効化しました"
    
    check_services
}

# サービス無効化
disable_services() {
    log_step "サービス自動起動を無効化中..."
    
    systemctl disable $WEBSOCKET_SERVICE
    log_info "✓ WebSocket転送サーバーの自動起動を無効化しました"
    
    systemctl disable $UDP_SERVICE
    log_info "✓ UDP受信プログラムの自動起動を無効化しました"
    
    check_services
}

# サービスアンインストール
uninstall_services() {
    log_step "サービスをアンインストール中..."
    
    # 確認
    read -p "本当にサービスをアンインストールしますか？ (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "アンインストールをキャンセルしました"
        return 0
    fi
    
    # サービス停止
    systemctl stop $WEBSOCKET_SERVICE $UDP_SERVICE 2>/dev/null || true
    
    # サービス無効化
    systemctl disable $WEBSOCKET_SERVICE $UDP_SERVICE 2>/dev/null || true
    
    # サービスファイル削除
    rm -f /etc/systemd/system/$WEBSOCKET_SERVICE
    rm -f /etc/systemd/system/$UDP_SERVICE
    
    # systemd再読み込み
    systemctl daemon-reload
    
    # ログローテーション設定削除
    rm -f /etc/logrotate.d/websocket-transfer
    
    # インストールディレクトリ削除
    read -p "インストールディレクトリ (/opt/websocket-transfer-server) を削除しますか？ (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf /opt/websocket-transfer-server
        log_info "✓ インストールディレクトリを削除しました"
    fi
    
    # ログディレクトリ削除
    read -p "ログディレクトリ (/var/log/websocket-transfer) を削除しますか？ (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf /var/log/websocket-transfer
        log_info "✓ ログディレクトリを削除しました"
    fi
    
    # サービスユーザー削除
    read -p "サービスユーザー (websocket) を削除しますか？ (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        userdel websocket 2>/dev/null || true
        groupdel websocket 2>/dev/null || true
        log_info "✓ サービスユーザーを削除しました"
    fi
    
    log_info "✓ アンインストールが完了しました"
}

# メイン処理
main() {
    case "${1:-}" in
        start)
            start_services
            ;;
        stop)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs
            ;;
        enable)
            enable_services
            ;;
        disable)
            disable_services
            ;;
        uninstall)
            uninstall_services
            ;;
        *)
            show_usage
            exit 1
            ;;
    esac
}

# スクリプト実行
main "$@"
