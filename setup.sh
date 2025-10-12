#!/bin/bash

# WebSocket Transfer Server Setup Script for Linux
# このスクリプトはLinux環境でWebSocket転送サーバーをセットアップします

set -e  # エラー時にスクリプトを停止

echo "=========================================="
echo "WebSocket Transfer Server Setup"
echo "=========================================="

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Pythonのバージョンチェック
check_python() {
    log_info "Pythonのバージョンをチェック中..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
        log_info "Python3が見つかりました: $PYTHON_VERSION"
        
        # バージョン3.7以上かチェック
        if python3 -c "import sys; exit(0 if sys.version_info >= (3, 7) else 1)" 2>/dev/null; then
            log_info "Python3.7以上が利用可能です"
        else
            log_error "Python3.7以上が必要です。現在のバージョン: $PYTHON_VERSION"
            exit 1
        fi
    else
        log_error "Python3が見つかりません。Python3.7以上をインストールしてください。"
        exit 1
    fi
}

# システム環境の準備
prepare_system() {
    log_info "システム環境を準備中..."
    
    # pip3が利用可能かチェック
    if ! command -v pip3 &> /dev/null; then
        log_error "pip3が見つかりません。Python3の開発パッケージをインストールしてください。"
        log_info "Ubuntu/Debian: sudo apt-get install python3-pip python3-venv"
        log_info "CentOS/RHEL: sudo yum install python3-pip"
        log_info "Fedora: sudo dnf install python3-pip"
        exit 1
    fi
    
    log_info "システム環境の準備が完了しました"
}

# 依存関係のインストール
install_dependencies() {
    log_info "依存関係をインストール中..."
    
    if [ ! -f "requirements.txt" ]; then
        log_error "requirements.txtが見つかりません"
        exit 1
    fi
    
    # pip3を最新版にアップグレード
    pip3 install --upgrade pip
    
    # 依存関係をシステム全体にインストール
    pip3 install -r requirements.txt
    
    log_info "依存関係のインストールが完了しました"
}

# サーバーファイルの存在確認
check_server_file() {
    log_info "サーバーファイルをチェック中..."
    
    if [ ! -f "server.py" ]; then
        log_error "server.pyが見つかりません"
        exit 1
    fi
    
    # 実行権限を付与
    chmod +x server.py
    log_info "server.pyに実行権限を付与しました"
}

# ポートの使用状況チェック
check_ports() {
    log_info "ポート8675と8775の使用状況をチェック中..."
    
    for port in 8675 8775; do
        if lsof -i :$port &> /dev/null; then
            log_warn "ポート$portは既に使用されています"
            log_warn "使用中のプロセス:"
            lsof -i :$port
        else
            log_info "ポート$portは利用可能です"
        fi
    done
}

# 起動テスト
test_startup() {
    log_info "サーバーの起動テストを実行中..."
    
    # バックグラウンドでサーバーを起動
    python3 server.py &
    SERVER_PID=$!
    
    # 3秒待機
    sleep 3
    
    # プロセスが動いているかチェック
    if kill -0 $SERVER_PID 2>/dev/null; then
        log_info "サーバーが正常に起動しました (PID: $SERVER_PID)"
        log_info "サーバーを停止中..."
        kill $SERVER_PID
        wait $SERVER_PID 2>/dev/null || true
        log_info "サーバーを停止しました"
    else
        log_error "サーバーの起動に失敗しました"
        exit 1
    fi
}

# 使用方法の表示
show_usage() {
    echo ""
    echo "=========================================="
    echo "セットアップ完了！"
    echo "=========================================="
    echo ""
    echo "サーバーを起動するには:"
    echo "  python3 server.py"
    echo ""
    echo "または:"
    echo "  ./server.py"
    echo ""
    echo "サーバーに接続するには:"
    echo "  ポート8675: ws://localhost:8675"
    echo "  ポート8775: ws://localhost:8775"
    echo ""
    echo "終了するには Ctrl+C を押してください"
    echo ""
}

# メイン処理
main() {
    echo "開始時刻: $(date)"
    echo ""
    
    # 各ステップを実行
    check_python
    prepare_system
    install_dependencies
    check_server_file
    check_ports
    test_startup
    show_usage
    
    echo "完了時刻: $(date)"
    log_info "セットアップが正常に完了しました！"
}

# スクリプト実行
main "$@"
