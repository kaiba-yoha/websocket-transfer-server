#!/bin/bash

# WebSocket Transfer Server 統合起動スクリプト
# WebSocket転送サーバーとUDP受信プログラムを同時起動

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

# プロセス管理
WEBSOCKET_PID=""
UDP_RECEIVER_PID=""

# クリーンアップ関数
cleanup() {
    log_info "システムを停止中..."
    
    if [ ! -z "$WEBSOCKET_PID" ]; then
        log_info "WebSocket転送サーバーを停止中... (PID: $WEBSOCKET_PID)"
        kill $WEBSOCKET_PID 2>/dev/null || true
    fi
    
    if [ ! -z "$UDP_RECEIVER_PID" ]; then
        log_info "UDP受信プログラムを停止中... (PID: $UDP_RECEIVER_PID)"
        kill $UDP_RECEIVER_PID 2>/dev/null || true
    fi
    
    log_info "システム停止完了"
    exit 0
}

# シグナルハンドリング
trap cleanup SIGINT SIGTERM

# メイン処理
main() {
    log_step "WebSocket Transfer Server 統合システムを起動中..."
    
    # 1. WebSocket転送サーバーの起動
    log_step "1. WebSocket転送サーバーを起動中..."
    cd server
    
    # 依存関係の確認
    if [ ! -d "venv" ]; then
        log_warn "仮想環境が見つかりません。セットアップを実行します..."
        ./setup.sh
    fi
    
    # 仮想環境の有効化（存在する場合）
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    # WebSocketサーバーをバックグラウンドで起動
    python server.py &
    WEBSOCKET_PID=$!
    log_info "WebSocket転送サーバー起動完了 (PID: $WEBSOCKET_PID)"
    
    # 2. UDP受信プログラムの起動
    log_step "2. UDP受信プログラムを起動中..."
    cd ../receiver
    
    # UDP受信プログラムをバックグラウンドで起動
    python udp_receiver.py &
    UDP_RECEIVER_PID=$!
    log_info "UDP受信プログラム起動完了 (PID: $UDP_RECEIVER_PID)"
    
    # 3. 起動確認
    log_step "3. システム起動確認中..."
    sleep 2
    
    # プロセスが動いているかチェック
    if kill -0 $WEBSOCKET_PID 2>/dev/null; then
        log_info "✓ WebSocket転送サーバー: 正常動作中"
    else
        log_error "✗ WebSocket転送サーバー: 起動失敗"
        exit 1
    fi
    
    if kill -0 $UDP_RECEIVER_PID 2>/dev/null; then
        log_info "✓ UDP受信プログラム: 正常動作中"
    else
        log_error "✗ UDP受信プログラム: 起動失敗"
        exit 1
    fi
    
    # 4. システム情報表示
    echo ""
    log_info "=========================================="
    log_info "システム起動完了！"
    log_info "=========================================="
    log_info "WebSocket転送サーバー: ws://localhost:8675, ws://localhost:8775"
    log_info "UDP受信プログラム: 127.0.0.1:8080"
    log_info ""
    log_info "終了するには Ctrl+C を押してください"
    log_info "=========================================="
    
    # 5. プロセス監視
    while true; do
        sleep 5
        
        # プロセス生存確認
        if ! kill -0 $WEBSOCKET_PID 2>/dev/null; then
            log_error "WebSocket転送サーバーが停止しました"
            cleanup
        fi
        
        if ! kill -0 $UDP_RECEIVER_PID 2>/dev/null; then
            log_error "UDP受信プログラムが停止しました"
            cleanup
        fi
    done
}

# スクリプト実行
main "$@"
